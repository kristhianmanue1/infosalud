"""Artefactos de la adquisición de octubre 2026 (ADR-014): perfiles
del CUUMSP septiembre 2026 y del IFU nacional agosto 2026 convertido
deben seguir válidos; huellas sincronizadas con las verificaciones
vigentes del catálogo. Las pruebas en vivo requieren los binarios
locales (data/descargas y data/convertidos no versionados).
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
ID_CUUMSP = "recursos-cuumsp-septiembre-2026"
ID_IFU_AGO = "recursos-ifu-nacional-agosto-2026-convertido"
XLSX_CUUMSP = (RAIZ / "data" / "descargas" / ID_CUUMSP
               / "CUUMSP_SEPTIEMBRE_2026_14092026.xlsx")
XLSX_IFU_AGO = (RAIZ / "data" / "convertidos"
                / "recursos-ifu-nacional-agosto-2026"
                / "IFU_nacional_Agosto2026_17092026.xlsx")


def _huella_vigente(id_fuente):
    catalogo = json.loads(
        (RAIZ / "data" / "fuentes.json").read_text(encoding="utf-8"))
    fuente = next(f for f in catalogo["fuentes"]
                  if f["id"] == id_fuente)
    return fuente["verificaciones"][-1]


class TestAdquisicionOctubre2026(unittest.TestCase):

    def test_perfil_cuumsp_septiembre_2026_valido(self):
        perfil = cargar_perfil(ruta_perfil(CATALOGO, ID_CUUMSP))
        self.assertEqual(validar(perfil), [])
        self.assertEqual(perfil["version_perfil"], 1)
        um = next(h for h in perfil["hojas"]
                  if h["nombre"] == "Unidad Médica")
        self.assertEqual(um["fila_encabezados"], 10)
        self.assertEqual(um["filas_datos"], {"desde": 11, "hasta": 1573})

    def test_perfil_cuumsp_huella_sincronizada(self):
        ver = _huella_vigente(ID_CUUMSP)
        perfil = cargar_perfil(ruta_perfil(CATALOGO, ID_CUUMSP))
        self.assertEqual(perfil["huella_base"], ver["huella"])

    def test_perfil_ifu_agosto_2026_convertido_valido(self):
        """Layout agostino: nota en 15, encabezados en 16, total
        Nacional en 17, datos 18..1601, dup y ceros al final."""
        perfil = cargar_perfil(ruta_perfil(CATALOGO, ID_IFU_AGO))
        self.assertEqual(validar(perfil), [])
        self.assertEqual(perfil["version_perfil"], 1)
        unidad = next(h for h in perfil["hojas"]
                      if h["nombre"] == "Unidad")
        self.assertEqual(unidad["fila_encabezados"], 16)
        self.assertEqual(unidad["filas_datos"],
                         {"desde": 18, "hasta": 1601})
        self.assertEqual(unidad["filas_total"], [17, 1602, 1603])
        grupo = unidad["conciliaciones"][0]
        self.assertEqual(grupo["nombre"], "Nacional")
        self.assertEqual(grupo["total_fila"], 17)
        esperado = {"Unidad": 182, "50100 Camas Censables": 112,
                    "60000 Camas No Censables": 50,
                    "71200 Especialidades": 118, "Quirófanos": 5,
                    "Equipamiento": 192, "OOAD_UMAE": 196}
        for h in perfil["hojas"]:
            if h["nombre"] in esperado:
                self.assertEqual(len(h["columnas_numericas"]),
                                 esperado[h["nombre"]], h["nombre"])
        solicitudes = next(h for h in perfil["hojas"]
                           if h["nombre"] == "IFU- Solicitudes")
        self.assertEqual(solicitudes["filas_datos"],
                         {"desde": 12, "hasta": 931})

    def test_perfil_ifu_agosto_huella_sincronizada(self):
        ver = _huella_vigente(ID_IFU_AGO)
        perfil = cargar_perfil(ruta_perfil(CATALOGO, ID_IFU_AGO))
        self.assertEqual(perfil["huella_base"], ver["huella"])

@unittest.skipUnless(XLSX_CUUMSP.is_file(),
                     "el xlsx del CUUMSP no está en el clone")
class TestCuumspSeptiembreEnVivo(unittest.TestCase):

    def test_hoja_unidad_medica_segmentada_sin_residual(self):
        perfil = cargar_perfil(ruta_perfil(CATALOGO, ID_CUUMSP))
        hojas = {h["hoja"]: h["filas"] for h in
                 leer_filas(str(XLSX_CUUMSP), max_filas=MAX_FILAS)}
        um = next(h for h in perfil["hojas"]
                  if h["nombre"] == "Unidad Médica")
        reporte = segmentar(um, hojas["Unidad Médica"], MAX_FILAS)
        self.assertEqual(reporte["fuera_de_rango"], 0)
        self.assertFalse(reporte["requiere_revision"])
        self.assertEqual(len(reporte["datos"]), 1573 - 11 + 1)


@unittest.skipUnless(XLSX_IFU_AGO.is_file(),
                     "el xlsx convertido del IFU no está en el clone")
class TestIfuAgostoEnVivo(unittest.TestCase):

    def test_conciliacion_nacional_reconciliada_en_las_7_hojas(self):
        perfil = cargar_perfil(ruta_perfil(CATALOGO, ID_IFU_AGO))
        hojas = {h["hoja"]: h["filas"] for h in
                 leer_filas(str(XLSX_IFU_AGO), max_filas=MAX_FILAS)}
        for declaracion in perfil["hojas"]:
            if not declaracion.get("conciliaciones"):
                continue
            reporte = segmentar(declaracion,
                                hojas[declaracion["nombre"]],
                                MAX_FILAS)
            conciliacion = reporte["conciliacion"]
            self.assertIsNotNone(conciliacion, declaracion["nombre"])
            self.assertTrue(conciliacion["reconciliado"],
                            declaracion["nombre"])
            self.assertEqual(
                conciliacion["grupos"][0]["columnas_descuadradas"],
                0, declaracion["nombre"])

    def test_hojas_tabulares_segmentadas_sin_residual(self):
        perfil = cargar_perfil(ruta_perfil(CATALOGO, ID_IFU_AGO))
        hojas = {h["hoja"]: h["filas"] for h in
                 leer_filas(str(XLSX_IFU_AGO), max_filas=MAX_FILAS)}
        esperado = {"IFU- BAJAS Y CAMBIOS": 5878 - 14 + 1,
                    "IFU- Solicitudes": 931 - 12 + 1}
        for declaracion in perfil["hojas"]:
            nombre = declaracion["nombre"]
            if nombre not in esperado:
                continue
            reporte = segmentar(declaracion, hojas[nombre], MAX_FILAS)
            self.assertEqual(reporte["fuera_de_rango"], 0, nombre)
            self.assertFalse(reporte["requiere_revision"], nombre)
            self.assertEqual(len(reporte["datos"]),
                             esperado[nombre], nombre)
