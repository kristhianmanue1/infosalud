"""Perfil IFU nacional diciembre 2025 convertido y dimensión ooad
(ADR-014): los artefactos de datos reales del repo deben seguir
válidos — perfil declarado, huella sincronizada con la verificación
vigente y dimensión ooad construible contra el catálogo convertido.
"""
import json
import unittest
from pathlib import Path

from infosalud.dimensiones import (
    construir as construir_dimension,
    cargar_config,
)
from infosalud.perfiles import (
    cargar as cargar_perfil,
    ruta_perfil,
    validar,
)

RAIZ = Path(__file__).resolve().parent.parent
CATALOGO = str(RAIZ / "data" / "fuentes.json")
ID_IFU = "recursos-ifu-nacional-diciembre-2025-convertido"


class TestPerfilIfuYOoad(unittest.TestCase):
    """Los artefactos de datos reales del repo deben seguir válidos:
    perfil declarado, huella sincronizada con la verificación vigente
    y dimensión ooad construible contra el catálogo convertido."""

    def test_perfil_ifu_convertido_valido(self):
        perfil = cargar_perfil(ruta_perfil(CATALOGO, ID_IFU))
        self.assertEqual(validar(perfil), [])
        self.assertEqual(perfil["version_perfil"], 1)
        tipos = {h["nombre"]: h["tipo"] for h in perfil["hojas"]}
        self.assertEqual(tipos.get("OOAD_UMAE"), "datos")
        self.assertEqual(tipos.get("Quirófanos"), "datos")
        self.assertEqual(tipos.get("Unidad"), "datos")

    def test_huella_del_perfil_coincide_con_verificacion_vigente(self):
        catalogo = json.loads(
            (RAIZ / "data" / "fuentes.json").read_text(encoding="utf-8"))
        fuente = next(f for f in catalogo["fuentes"]
                      if f["id"] == ID_IFU)
        huella = fuente["verificaciones"][-1]["huella"]
        perfil = cargar_perfil(ruta_perfil(CATALOGO, ID_IFU))
        self.assertEqual(perfil["huella_base"], huella)

    def test_dimension_ooad_configurada_y_construible(self):
        config = cargar_config(CATALOGO)
        self.assertIsNotNone(config)
        self.assertIn("ooad", config["dimensiones"])
        cuerpo = construir_dimension(
            CATALOGO, "ooad", **config["dimensiones"]["ooad"])
        self.assertEqual(cuerpo["contrato"], "dimension-v1")
        self.assertGreaterEqual(cuerpo["total"], 30)
        self.assertEqual(cuerpo["sin_clave"], 0)
        claves = cuerpo["claves"]
        # El catálogo guarda CVE_DELEGACION numérica, sin cero inicial.
        self.assertIn("1", claves)
        self.assertTrue(claves["1"]["DESC_DELEGACION"]
                        .strip().lower().startswith("aguascalientes"))
