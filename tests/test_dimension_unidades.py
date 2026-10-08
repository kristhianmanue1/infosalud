"""Dimensión canónica `unidades` (ADR-016): el maestro de unidades
por Clave Presupuestal debe seguir válido, con unicidad de clave
(ronda adversarial 2026-10-08, H-1), atributos completos (H-6),
integridad verificada (H-7) y consistencia con la dimensión `ooad`.
Las pruebas de construcción requieren el archivo local verificado
(data/descargas no versionado).
"""
import unittest
from pathlib import Path

from infosalud.dimensiones import (
    construir,
    cargar_config,
)
from infosalud.estructura import leer_filas
from infosalud.exportar import MAX_FILAS
from infosalud.perfiles import ruta_perfil, cargar as cargar_perfil

RAIZ = Path(__file__).resolve().parent.parent
CATALOGO = str(RAIZ / "data" / "fuentes.json")
ID_CUUMSP = "recursos-cuumsp-septiembre-2026"
CLAVE = "Clave Presupuestal"


class TestConfigDimensionUnidades(unittest.TestCase):
    """Configuración: no requiere el archivo local."""

    def test_dimension_declarada_con_fuente_concreta(self):
        config = cargar_config(CATALOGO)
        self.assertIsNotNone(config)
        self.assertIn("unidades", config["dimensiones"])
        spec = config["dimensiones"]["unidades"]
        self.assertEqual(spec["fuente"], ID_CUUMSP)
        self.assertEqual(spec["hoja"], "Unidad Médica")
        self.assertEqual(spec["clave"], CLAVE)
        self.assertGreaterEqual(len(spec["atributos"]), 10)

    def test_atributos_existen_verbatim_en_el_perfil(self):
        """H-2/H-6: cada atributo debe existir tal cual en las
        columnas del perfil de la fuente."""
        config = cargar_config(CATALOGO)
        spec = config["dimensiones"]["unidades"]
        perfil = cargar_perfil(ruta_perfil(CATALOGO, spec["fuente"]))
        columnas = next(h for h in perfil["hojas"]
                        if h["nombre"] == spec["hoja"])["columnas"]
        for atributo in spec["atributos"]:
            self.assertIn(atributo, columnas, atributo)


@unittest.skipUnless(
    (RAIZ / "data" / "descargas" / ID_CUUMSP).is_dir(),
    "el xlsx del CUUMSP no está en el clone")
class TestDimensionUnidadesEnVivo(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = cargar_config(CATALOGO)
        cls.spec = cls.config["dimensiones"]["unidades"]
        cls.cuerpo = construir(
            CATALOGO, "unidades", cls.spec["fuente"],
            cls.spec["hoja"], cls.spec["clave"],
            cls.spec["atributos"])

    def test_contrato_y_total(self):
        self.assertEqual(self.cuerpo["contrato"], "dimension-v1")
        self.assertEqual(self.cuerpo["total"], 1563)
        self.assertEqual(self.cuerpo["sin_clave"], 0)
        self.assertNotIn("atributos_omitidos", self.cuerpo)

    def test_integridad_verificada(self):
        """H-7: la procedencia hereda el fail-closed de sha256."""
        procedencia = self.cuerpo["procedencia"]
        self.assertEqual(procedencia["estado_integridad"],
                         "verificado")
        self.assertEqual(procedencia["sha256"],
                         procedencia["sha256_registrado"])

    def test_unicidad_de_clave_rederivada_del_archivo(self):
        """H-1: la unicidad se re-deriva del archivo real, no del
        dict que colapsaría duplicados en silencio."""
        perfil = cargar_perfil(ruta_perfil(CATALOGO, ID_CUUMSP))
        um = next(h for h in perfil["hojas"]
                  if h["nombre"] == "Unidad Médica")
        ver = next(f for f in json_catalogo()["fuentes"]
                   if f["id"] == ID_CUUMSP)["verificaciones"][-1]
        filas = {x["hoja"]: x["filas"] for x in
                 leer_filas(str(RAIZ / ver["ruta_local"]),
                            max_filas=MAX_FILAS)}["Unidad Médica"]
        indice = um["columnas"].index(CLAVE)
        desde = um["filas_datos"]["desde"]
        hasta = um["filas_datos"]["hasta"]
        claves = {str(filas[r - 1][indice]).strip()
                  for r in range(desde, hasta + 1)}
        n_filas = hasta - desde + 1
        self.assertEqual(len(claves), n_filas)
        self.assertEqual(set(self.cuerpo["claves"]), claves)

    def test_consistencia_con_la_dimension_ooad(self):
        """Toda OOAD oficial (dimensión ooad) debe aparecer entre
        las delegaciones/UMAE del maestro (normalizando el cero
        inicial)."""
        ooad = construir(CATALOGO, "ooad",
                         "catalogo-ooad-subdelegaciones-convertido",
                         "febrero 2025", "CVE_DELEGACION",
                         ["DESC_DELEGACION"])
        valores = {c["Clave Delegación o UMAE"]
                   for c in self.cuerpo["claves"].values()}
        normalizados = {str(int(v)) for v in valores
                        if v.isdigit()}
        for clave_ooad in ooad["claves"]:
            self.assertIn(clave_ooad, normalizados, clave_ooad)


def json_catalogo():
    import json
    return json.loads(
        (RAIZ / "data" / "fuentes.json").read_text(
            encoding="utf-8"))
