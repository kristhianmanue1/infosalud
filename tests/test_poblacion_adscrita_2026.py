"""Serie Población Adscrita 2026 (ADR-014): los 8 perfiles mensuales
deben seguir válidos, con huella sincronizada a la verificación
del catálogo y doble conciliación (Unidades y OOAD vs Nacional).
Las pruebas en vivo requieren los binarios locales (data/descargas
no versionado).
"""
import json
import unittest
from pathlib import Path

from infosalud.datos import segmentar
from infosalud.estructura import leer_filas
from infosalud.exportar import MAX_FILAS
from infosalud.perfiles import (
    cargar as cargar_perfil,
    ruta_perfil,
    validar,
)

RAIZ = Path(__file__).resolve().parent.parent
CATALOGO = str(RAIZ / "data" / "fuentes.json")
MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago")
IDS = tuple(f"poblacion-adscrita-{m}-2026" for m in MESES)


def _ruta_local(id_fuente):
    catalogo = json.loads(
        (RAIZ / "data" / "fuentes.json").read_text(encoding="utf-8"))
    fuente = next(f for f in catalogo["fuentes"]
                  if f["id"] == id_fuente)
    ver = fuente["verificaciones"][-1]
    return ver["ruta_local"], ver["huella"]


class TestPoblacionAdscrita2026(unittest.TestCase):

    def test_los_8_perfiles_son_validos(self):
        for id_fuente in IDS:
            perfil = cargar_perfil(ruta_perfil(CATALOGO, id_fuente))
            self.assertEqual(validar(perfil), [], id_fuente)
            self.assertEqual(perfil["version_perfil"], 1, id_fuente)

    def test_layout_y_conciliacion_doble_declarada(self):
        for id_fuente in IDS:
            perfil = cargar_perfil(ruta_perfil(CATALOGO, id_fuente))
            hoja = perfil["hojas"][0]
            self.assertEqual(hoja["nombre"], "Pob. Adsc.", id_fuente)
            self.assertEqual(hoja["fila_encabezados"], 10, id_fuente)
            self.assertEqual(hoja["filas_datos"]["desde"], 12,
                             id_fuente)
            self.assertEqual(hoja["filas_total"], [11], id_fuente)
            self.assertEqual(len(hoja["columnas_numericas"]), 8,
                             id_fuente)
            grupos = {g["nombre"]: g
                      for g in hoja["conciliaciones"]}
            self.assertEqual(set(grupos), {"Unidades", "OOAD"},
                             id_fuente)
            self.assertEqual(len(grupos["OOAD"]["filas"]), 35,
                             id_fuente)
            self.assertEqual(
                len(grupos["Unidades"]["filas"])
                + len(grupos["OOAD"]["filas"]),
                hoja["filas_datos"]["hasta"] - 12 + 1, id_fuente)

    def test_huellas_sincronizadas_con_el_catalogo(self):
        for id_fuente in IDS:
            _, huella = _ruta_local(id_fuente)
            perfil = cargar_perfil(ruta_perfil(CATALOGO, id_fuente))
            self.assertEqual(perfil["huella_base"], huella, id_fuente)

    def test_indice_registrado_como_html(self):
        catalogo = json.loads(
            (RAIZ / "data" / "fuentes.json").read_text(encoding="utf-8"))
        indice = next(f for f in catalogo["fuentes"]
                      if f["id"] == "poblacion-adscrita-2026")
        self.assertEqual(indice["formato"], "html")
        hijos = [f for f in catalogo["fuentes"]
                 if f.get("parent_source_id")
                 == "poblacion-adscrita-2026"]
        self.assertEqual(len(hijos), 8)


@unittest.skipUnless(
    (RAIZ / "data" / "descargas" / "poblacion-adscrita-ago-2026")
    .is_dir(), "los xlsx de población no están en el clone")
class TestPoblacionAdscritaEnVivo(unittest.TestCase):

    def test_conciliacion_doble_reconciliada(self):
        for id_fuente in IDS:
            ruta, _ = _ruta_local(id_fuente)
            hojas = {h["hoja"]: h["filas"] for h in
                     leer_filas(str(RAIZ / ruta),
                                max_filas=MAX_FILAS)}
            perfil = cargar_perfil(ruta_perfil(CATALOGO, id_fuente))
            reporte = segmentar(perfil["hojas"][0],
                                hojas["Pob. Adsc."], MAX_FILAS)
            self.assertEqual(reporte["fuera_de_rango"], 0, id_fuente)
            self.assertFalse(reporte["requiere_revision"], id_fuente)
            for grupo in reporte["conciliacion"]["grupos"]:
                self.assertTrue(grupo["reconciliado"],
                                (id_fuente, grupo["nombre"]))
                self.assertEqual(grupo["columnas_descuadradas"], 0,
                                 (id_fuente, grupo["nombre"]))
