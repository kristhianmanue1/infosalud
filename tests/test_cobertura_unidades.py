"""SPEC-14 (ADR-016): cobertura de la dimensión `unidades`.
Dentro/fuera contra el maestro con subtotales excluidos y lista
explícita de claves fuera. Las pruebas de construcción requieren
los binarios verificados locales (data/descargas y
data/convertidos no versionados).
"""
import json
import unittest
from pathlib import Path

from infosalud.cobertura import (
    construir,
    cargar_config,
    es_subtotal,
    ruta_config,
    ErrorDimension,
)

RAIZ = Path(__file__).resolve().parent.parent
CATALOGO = str(RAIZ / "data" / "fuentes.json")


class TestConfigCobertura(unittest.TestCase):

    def test_config_declarada_con_dos_fuentes(self):
        config = cargar_config(CATALOGO)
        self.assertIsNotNone(config)
        self.assertEqual(len(config["fuentes"]), 2)
        for entrada in config["fuentes"]:
            self.assertEqual(
                set(entrada), {"fuente", "hoja", "columna"})

    def test_sin_config_da_404(self):
        dir_tmp = Path(__file__).parent / "__tmp_sin_config__"
        dir_tmp.mkdir(exist_ok=True)
        try:
            catalogo = str(dir_tmp / "fuentes.json")
            Path(catalogo).write_text(
                json.dumps({"version": 1, "fuentes": []}),
                encoding="utf-8")
            with self.assertRaises(ErrorDimension) as ctx:
                construir(catalogo)
            self.assertEqual(ctx.exception.codigo, 404)
        finally:
            (dir_tmp / "fuentes.json").unlink(missing_ok=True)
            dir_tmp.rmdir()

    def test_config_con_campo_extra_rechazada(self):
        dir_tmp = Path(__file__).parent / "__tmp_cfg_mala__"
        dir_tmp.mkdir(exist_ok=True)
        try:
            catalogo = str(dir_tmp / "fuentes.json")
            Path(catalogo).write_text(
                json.dumps({"version": 1, "fuentes": []}),
                encoding="utf-8")
            Path(dir_tmp / "cobertura-unidades.json").write_text(
                json.dumps({"version": 1, "fuentes": [
                    {"fuente": "x", "hoja": "y", "columna": "z",
                     "extra": 1}]}),
                encoding="utf-8")
            with self.assertRaises(ErrorDimension) as ctx:
                cargar_config(catalogo)
            self.assertEqual(ctx.exception.codigo, 500)
        finally:
            for nombre in ("fuentes.json",
                           "cobertura-unidades.json"):
                (dir_tmp / nombre).unlink(missing_ok=True)
            dir_tmp.rmdir()

    def test_es_subtotal(self):
        self.assertTrue(es_subtotal("000000000000"))
        self.assertTrue(es_subtotal("010000000000"))
        self.assertFalse(es_subtotal("010106252110"))
        self.assertFalse(es_subtotal("38A584252110"))


@unittest.skipUnless(
    (RAIZ / "data" / "descargas" / "poblacion-adscrita-ago-2026")
    .is_dir(),
    "los binarios verificados no están en el clone")
class TestCoberturaEnVivo(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cuerpo = construir(CATALOGO)

    def test_contrato_y_maestro(self):
        self.assertEqual(self.cuerpo["contrato"],
                         "cobertura-unidades-v1")
        self.assertEqual(self.cuerpo["maestro"]["total"], 1563)
        self.assertEqual(self.cuerpo["procedencia"]
                         ["estado_integridad"], "verificado")

    def test_numeros_de_cobertura_con_subtotales_excluidos(self):
        esperado = {
            "recursos-ifu-nacional-agosto-2026-convertido":
                (1584, 1559, 25),
            "poblacion-adscrita-ago-2026": (1288, 1271, 17),
        }
        for fila in self.cuerpo["fuentes"]:
            total, dentro, fuera = esperado[fila["fuente"]]
            self.assertEqual((fila["total"], fila["dentro"],
                              fila["fuera"]), (total, dentro, fuera),
                             fila["fuente"])
            self.assertEqual(len(fila["fuera_claves"]), fuera,
                             fila["fuente"])
            for clave in fila["fuera_claves"]:
                self.assertFalse(es_subtotal(clave),
                                 (fila["fuente"], clave))

    def test_dimension_sin_cobertura_da_404(self):
        with self.assertRaises(ErrorDimension) as ctx:
            construir(CATALOGO, "ooad")
        # ooad sí está declarada como dimensión, pero sin cobertura
        self.assertEqual(ctx.exception.codigo, 404)
