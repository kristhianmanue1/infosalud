"""Perfil IFU nacional diciembre 2025 convertido y dimensión ooad
(ADR-014): los artefactos de datos reales del repo deben seguir
válidos — perfil declarado, huella sincronizada con la verificación
vigente y dimensión ooad construible contra el catálogo convertido.
"""
import json
import unittest
from pathlib import Path

from infosalud.datos import segmentar
from infosalud.estructura import leer_filas
from infosalud.exportar import MAX_FILAS
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
XLSX = (RAIZ / "data" / "convertidos"
        / "recursos-ifu-nacional-diciembre-2025"
        / "IFU_nacional_Diciembre2025_21012026.xlsx")
TABULARES = ("Unidad", "50100 Camas Censables",
             "60000 Camas No Censables", "71200 Especialidades",
             "Quirófanos", "Equipamiento", "OOAD_UMAE")


class TestPerfilIfuYOoad(unittest.TestCase):
    """Los artefactos de datos reales del repo deben seguir válidos:
    perfil declarado, huella sincronizada con la verificación vigente
    y dimensión ooad construible contra el catálogo convertido."""

    def test_perfil_ifu_convertido_valido(self):
        perfil = cargar_perfil(ruta_perfil(CATALOGO, ID_IFU))
        self.assertEqual(validar(perfil), [])
        self.assertEqual(perfil["version_perfil"], 2)
        tipos = {h["nombre"]: h["tipo"] for h in perfil["hojas"]}
        self.assertEqual(tipos.get("OOAD_UMAE"), "datos")
        self.assertEqual(tipos.get("Quirófanos"), "datos")
        self.assertEqual(tipos.get("Unidad"), "datos")

    def test_perfil_v2_fase3_hojas_tabulares_declaradas(self):
        """Fase 3: BAJAS Y CAMBIOS y Solicitudes pasan de
        descriptivas a datos, con layout declarado y sin conciliación
        (la fuente no trae filas de total para esas hojas)."""
        perfil = cargar_perfil(ruta_perfil(CATALOGO, ID_IFU))
        por_nombre = {h["nombre"]: h for h in perfil["hojas"]}
        datos = [h for h in perfil["hojas"] if h["tipo"] == "datos"]
        self.assertEqual(len(datos), 9)
        bajas = por_nombre["IFU- BAJAS Y CAMBIOS"]
        self.assertEqual(bajas["fila_encabezados"], 13)
        self.assertEqual(bajas["filas_datos"], {"desde": 14, "hasta": 5878})
        self.assertEqual(bajas["columnas_numericas"],
                         ["Valor Actual", "Valor Unidad",
                          "Valor Delegación", "Valor Normativa",
                          "Valor Final IFU"])
        self.assertNotIn("conciliaciones", bajas)
        solicitudes = por_nombre["IFU- Solicitudes"]
        self.assertEqual(solicitudes["fila_encabezados"], 11)
        self.assertEqual(solicitudes["filas_datos"],
                         {"desde": 12, "hasta": 1297})
        self.assertNotIn("columnas_numericas", solicitudes)
        self.assertNotIn("conciliaciones", solicitudes)

    def test_perfil_v2_fase3_numericas_y_conciliacion_nacional(self):
        """Fase 3: las 7 hojas tabulares declaran columnas_numericas
        y un grupo de conciliación Nacional contra la fila 16."""
        perfil = cargar_perfil(ruta_perfil(CATALOGO, ID_IFU))
        tabulares = ("Unidad", "50100 Camas Censables",
                     "60000 Camas No Censables", "71200 Especialidades",
                     "Quirófanos", "Equipamiento", "OOAD_UMAE")
        esperado = {"Unidad": 182, "50100 Camas Censables": 116,
                    "60000 Camas No Censables": 50,
                    "71200 Especialidades": 126, "Quirófanos": 5,
                    "Equipamiento": 192, "OOAD_UMAE": 196}
        for h in perfil["hojas"]:
            if h["nombre"] not in tabulares:
                continue
            numericas = h["columnas_numericas"]
            self.assertEqual(len(numericas), esperado[h["nombre"]],
                             h["nombre"])
            self.assertTrue(set(numericas) <= set(h["columnas"]),
                            h["nombre"])
            grupos = h["conciliaciones"]
            self.assertEqual(len(grupos), 1, h["nombre"])
            grupo = grupos[0]
            self.assertEqual(grupo["nombre"], "Nacional", h["nombre"])
            self.assertEqual(grupo["total_fila"], 16, h["nombre"])
            self.assertNotIn(16, grupo["filas"], h["nombre"])

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


@unittest.skipUnless(XLSX.is_file(),
                     "el xlsx convertido no está en el clone "
                     "(data/convertidos no versionado)")
class TestPerfilIfuFase3EnVivo(unittest.TestCase):
    """Verificación contra el archivo real por el camino del runtime
    (segmentar): conciliación Nacional reconciliada en las 7 hojas
    tabulares y las 2 hojas nuevas segmentadas sin residual."""

    @classmethod
    def setUpClass(cls):
        cls.perfil = cargar_perfil(ruta_perfil(CATALOGO, ID_IFU))
        cls.hojas = {h["hoja"]: h["filas"] for h in
                     leer_filas(str(XLSX), max_filas=MAX_FILAS)}

    def test_conciliacion_nacional_reconciliada_en_las_7_hojas(self):
        for declaracion in self.perfil["hojas"]:
            if declaracion["nombre"] not in TABULARES:
                continue
            reporte = segmentar(declaracion,
                                self.hojas[declaracion["nombre"]],
                                MAX_FILAS)
            conciliacion = reporte["conciliacion"]
            self.assertIsNotNone(conciliacion, declaracion["nombre"])
            self.assertTrue(conciliacion["reconciliado"],
                            declaracion["nombre"])
            grupo = conciliacion["grupos"][0]
            self.assertEqual(grupo["nombre"], "Nacional")
            self.assertEqual(grupo["columnas_descuadradas"], 0,
                             declaracion["nombre"])
            self.assertGreater(grupo["columnas_conciliadas"], 0,
                               declaracion["nombre"])

    def test_hojas_tabulares_segmentadas_sin_residual(self):
        esperado_datos = {"IFU- BAJAS Y CAMBIOS": 5878 - 14 + 1,
                          "IFU- Solicitudes": 1297 - 12 + 1}
        for declaracion in self.perfil["hojas"]:
            nombre = declaracion["nombre"]
            if nombre not in esperado_datos:
                continue
            reporte = segmentar(declaracion, self.hojas[nombre],
                                MAX_FILAS)
            self.assertEqual(reporte["tipo"], "datos")
            self.assertEqual(len(reporte["datos"]),
                             esperado_datos[nombre], nombre)
            self.assertEqual(reporte["fuera_de_rango"], 0, nombre)
            self.assertFalse(reporte["requiere_revision"], nombre)
            self.assertFalse(reporte["truncado"], nombre)
            self.assertIsNone(reporte["conciliacion"], nombre)
