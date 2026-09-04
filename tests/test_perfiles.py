"""SPEC-11 (ADR-014 fase 1): perfil estructural de una fuente.

Casos DADO/CUANDO/ENTONCES sobre CONTRATO perfil-de-fuente v1:
validación cerrada, procedencia obligatoria (huella_base),
tipo=datos exige columnas y filas_datos, los totales viven FUERA
del rango, y escritura atómica con carga fail-closed.
"""

import json
import tempfile
import unittest
from pathlib import Path

from infosalud.perfiles import (
    ErrorPerfil,
    cargar,
    guardar,
    ruta_perfil,
    validar,
)

HUELLA = "a" * 64
PERFIL_VALIDO = {
    "id": "fuente-prueba",
    "huella_base": HUELLA,
    "fecha": "2026-09-03",
    "version_perfil": 1,
    "hojas": [
        {
            "nombre": "Datos",
            "tipo": "datos",
            "fila_encabezados": 4,
            "columnas": ["clave_um", "nombre_um", "pamf"],
            "filas_datos": {"desde": 5, "hasta": 1742},
            "clave_primaria": "clave_um",
            "columnas_numericas": ["pamf"],
            "filas_total": [1, 2],
            "tolerancia": 0.005,
        },
        {"nombre": "Metodología", "tipo": "descriptiva"},
    ],
}


class PruebaValidarPerfil(unittest.TestCase):
    def test_perfil_valido_sin_errores(self):
        """DADO un perfil válido (encabezado en fila 4, rango 5..1742,
        totales fuera) CUANDO se valida ENTONCES cero errores."""
        self.assertEqual(validar(PERFIL_VALIDO), [])

    def test_campo_no_declarado_rechazado(self):
        """DADO un campo fuera del esquema ENTONCES rechazo nombrando
        el campo (esquema cerrado)."""
        perfil = dict(PERFIL_VALIDO, extra=1)
        self.assertTrue(any("extra" in e for e in validar(perfil)))

    def test_procedencia_obligatoria(self):
        """DADO huella_base ausente o no-hex ENTONCES rechazo (la
        procedencia nunca se pierde, ADR-014)."""
        for malo in (None, "xyz"):
            perfil = dict(PERFIL_VALIDO)
            if malo is None:
                perfil.pop("huella_base")
            else:
                perfil["huella_base"] = malo
            self.assertTrue(any("huella_base" in e
                                for e in validar(perfil)))

    def test_tipo_datos_exige_columnas_y_rango(self):
        """DADO tipo=datos sin columnas o sin filas_datos ENTONCES
        rechazo con motivo explícito."""
        hoja = dict(PERFIL_VALIDO["hojas"][0])
        for quitar in ("columnas", "filas_datos"):
            hoja_sin = dict(hoja)
            hoja_sin.pop(quitar)
            perfil = dict(PERFIL_VALIDO, hojas=[hoja_sin])
            self.assertTrue(any(quitar in e
                                for e in validar(perfil)))

    def test_columnas_con_huecos_posicionales(self):
        """DADO columnas con celdas vacías de posición (columna A sin
        encabezado en el origen) CUANDO se valida ENTONCES es válido
        (los vacíos son posiciones, no nombres)."""
        hoja = dict(PERFIL_VALIDO["hojas"][0],
                    columnas=["", "OOAD", "CVE_PRESUPUESTAL"])
        hoja.pop("columnas_numericas", None)
        hoja["clave_primaria"] = "CVE_PRESUPUESTAL"
        perfil = dict(PERFIL_VALIDO, hojas=[hoja])
        self.assertEqual(validar(perfil), [])

    def test_fila_encabezados_sub(self):
        """DADO una hoja con encabezado compuesto CUANDO se valida
        ENTONCES acepta la fila sub posterior y rechaza la anterior
        o igual a la principal (enmienda 2026-09-04)."""
        base = dict(PERFIL_VALIDO["hojas"][0])
        ok = dict(base, fila_encabezados=3, fila_encabezados_sub=4)
        self.assertEqual(validar(dict(PERFIL_VALIDO, hojas=[ok])), [])
        mal = dict(base, fila_encabezados=4, fila_encabezados_sub=4)
        self.assertTrue(any("fila_encabezados_sub" in e
                            for e in validar(dict(PERFIL_VALIDO,
                                                  hojas=[mal]))))

    def test_segmentar_expone_encabezados_sub(self):
        """DADO un perfil con fila_encabezados_sub CUANDO segmentar
        ENTONCES la respuesta incluye ambas filas de encabezado."""
        from infosalud.datos import segmentar
        filas = [["Clave", "Grupo"], ["", "Total"], ["01", "5"],
                 ["02", "7"]]
        declaracion = {"nombre": "H", "tipo": "datos",
                       "fila_encabezados": 1,
                       "fila_encabezados_sub": 2,
                       "columnas": ["Clave", "Grupo"],
                       "filas_datos": {"desde": 3, "hasta": 4}}
        r = segmentar(declaracion, filas, 100)
        self.assertEqual(r["encabezados"], ["Clave", "Grupo"])
        self.assertEqual(r["encabezados_sub"], ["", "Total"])
        self.assertEqual(r["datos"], [["01", "5"], ["02", "7"]])
        self.assertEqual(r["fuera_de_rango"], 0)

    def test_segmentos_validos_e_invalidos(self):
        """DADO una hoja multi-bloque CUANDO se valida ENTONCES
        acepta ≥2 segmentos con nombre único y rechaza: un solo
        segmento, campos de hoja junto a segmentos, nombres
        duplicados y totales dentro del rango del segmento."""
        segmento_a = {"nombre": "Medicina Familiar",
                      "fila_encabezados": 14,
                      "columnas": ["OOAD/UMAE", "2019", "2020"],
                      "filas_datos": {"desde": 17, "hasta": 76}}
        segmento_b = {"nombre": "Especialidades",
                      "fila_encabezados": 14,
                      "columnas": ["OOAD/UMAE", "2019", "2020"],
                      "filas_datos": {"desde": 17, "hasta": 76}}
        ok = dict(PERFIL_VALIDO["hojas"][0])
        hoja_multi = {"nombre": "Multi", "tipo": "datos",
                      "segmentos": [segmento_a, segmento_b]}
        self.assertEqual(validar(dict(PERFIL_VALIDO,
                                      hojas=[hoja_multi])), [])
        # un solo segmento no tiene sentido
        uno = dict(hoja_multi, segmentos=[segmento_a])
        self.assertTrue(any("segmentos" in e
                            for e in validar(dict(PERFIL_VALIDO,
                                                  hojas=[uno]))))
        # campo de hoja junto a segmentos
        mezcla = dict(hoja_multi, filas_datos={"desde": 1,
                                               "hasta": 2})
        self.assertTrue(any("filas_datos" in e
                            for e in validar(dict(PERFIL_VALIDO,
                                                  hojas=[mezcla]))))
        # nombre duplicado
        dup = dict(hoja_multi, segmentos=[segmento_a, segmento_a])
        self.assertTrue(any("duplicado" in e
                            for e in validar(dict(PERFIL_VALIDO,
                                                  hojas=[dup]))))
        # total dentro del rango del segmento
        con_total = dict(segmento_a, filas_total=[20])
        mal = dict(hoja_multi, segmentos=[con_total, segmento_b])
        self.assertTrue(any("filas_total" in e
                            for e in validar(dict(PERFIL_VALIDO,
                                                  hojas=[mal]))))

    def test_conciliacion_numerica(self):
        """DADO columnas numéricas y fila de total declarada CUANDO
        segmentar ENTONCES Σ(detalles) ≈ total con tolerancia;
        DADO un total descuadrado ENTONCES reconciliado false con
        ejemplos (parser tolera comas de millar)."""
        from infosalud.datos import segmentar
        declaracion = {"nombre": "H", "tipo": "datos",
                       "fila_encabezados": 1,
                       "columnas": ["CLAVE", "Poblacion"],
                       "columnas_numericas": ["Poblacion"],
                       "filas_datos": {"desde": 3, "hasta": 4},
                       "filas_total": [1], "tolerancia": 0.005}
        filas = [["Total Nacional", "56.17"],
                 ["CLAVE", "Poblacion"],
                 ["01", "20.5"],
                 ["02", "35.67"]]
        r = segmentar(declaracion, filas, 100)
        c = r["conciliacion"]
        self.assertTrue(c["reconciliado"])
        self.assertEqual(c["filas"][0]["columnas_conciliadas"], 1)
        filas[0] = ["Total Nacional", "99"]
        r = segmentar(declaracion, filas, 100)
        c = r["conciliacion"]
        self.assertFalse(c["reconciliado"])
        self.assertTrue(c["filas"][0]["ejemplos_descuadre"])

    def test_conciliacion_no_aplica_sin_numericas(self):
        """DADO filas_total sin columnas_numericas CUANDO segmentar
        ENTONCES conciliacion es None (no se inventan sumas)."""
        from infosalud.datos import segmentar
        declaracion = {"nombre": "H", "tipo": "datos",
                       "fila_encabezados": 1,
                       "columnas": ["CLAVE", "Poblacion"],
                       "filas_datos": {"desde": 2, "hasta": 3},
                       "filas_total": [1]}
        r = segmentar(declaracion,
                      [["Total", "5"], ["01", "2"], ["02", "3"]], 100)
        self.assertIsNone(r["conciliacion"])

    def test_filas_nota_validacion(self):
        """DADO filas_nota declaradas FUERA del rango CUANDO se
        valida ENTONCES es válido; dentro del rango ENTONCES
        rechazo (enmienda 2026-09-04)."""
        base = dict(PERFIL_VALIDO["hojas"][0])
        ok = dict(base, filas_nota=[1744])
        self.assertEqual(validar(dict(PERFIL_VALIDO, hojas=[ok])), [])
        mal = dict(base, filas_nota=[10])
        self.assertTrue(any("filas_nota" in e
                            for e in validar(dict(PERFIL_VALIDO,
                                                  hojas=[mal]))))

    def test_segmentar_excluye_notas_de_fuera_de_rango(self):
        """DADO una fila de nota después del rango declarada en
        filas_nota CUANDO segmentar ENTONCES no cuenta como
        fuera_de_rango (no requiere_revision por una nota)."""
        from infosalud.datos import segmentar
        declaracion = {"nombre": "H", "tipo": "datos",
                       "fila_encabezados": 1,
                       "columnas": ["CLAVE", "VALOR"],
                       "filas_datos": {"desde": 2, "hasta": 3},
                       "filas_nota": [4]}
        filas = [["CLAVE", "VALOR"], ["01", "5"], ["02", "6"],
                 ["**", "Conforme a lo indicado"], ["99", "NUEVA"]]
        r = segmentar(declaracion, filas, 100)
        self.assertEqual(r["fuera_de_rango"], 1)  # sólo la 99 NUEVA
        self.assertTrue(r["requiere_revision"])

    def test_segmentar_multi_bloque(self):
        """DADO una hoja con dos segmentos CUANDO segmentar ENTONCES
        la respuesta trae cada tabla independiente con su nombre,
        encabezados, datos y totales."""
        from infosalud.datos import segmentar
        declaracion = {"nombre": "Multi", "tipo": "datos",
                       "segmentos": [
                           {"nombre": "Medicina Familiar",
                            "fila_encabezados": 1,
                            "columnas": ["OOAD", "2019"],
                            "filas_datos": {"desde": 2, "hasta": 3},
                            "filas_total": []},
                           {"nombre": "Especialidades",
                            "fila_encabezados": 5,
                            "columnas": ["OOAD", "2019"],
                            "filas_datos": {"desde": 6, "hasta": 7},
                            "filas_total": []}]}
        filas = [["OOAD", "2019"], ["AGU", "10"], ["BCN", "20"],
                 ["", ""], ["OOAD", "2019"], ["AGU", "1"],
                 ["BCN", "2"], ["", ""]]
        r = segmentar(declaracion, filas, 100)
        self.assertEqual(r["tipo"], "datos")
        segmentos = r["segmentos"]
        self.assertEqual([s["nombre"] for s in segmentos],
                         ["Medicina Familiar", "Especialidades"])
        self.assertEqual(segmentos[0]["datos"],
                         [["AGU", "10"], ["BCN", "20"]])
        self.assertEqual(segmentos[1]["datos"],
                         [["AGU", "1"], ["BCN", "2"]])
        self.assertTrue(all(s["fuera_de_rango"] == 0
                            for s in segmentos))

    def test_segmentar_ignora_celdas_basura(self):
        """DADO filas posteriores al rango con celdas de sólo
        espacios o apóstrofes (artefactos de conversión) CUANDO
        segmentar ENTONCES no cuentan como fuera_de_rango."""
        from infosalud.datos import segmentar
        declaracion = {"nombre": "H", "tipo": "datos",
                       "fila_encabezados": 1,
                       "columnas": ["CLAVE", "VALOR"],
                       "filas_datos": {"desde": 2, "hasta": 3}}
        filas = [["CLAVE", "VALOR"], ["01", "5"], ["02", "6"],
                 [" ", "  "], ["", "   "]]
        r = segmentar(declaracion, filas, 100)
        self.assertEqual(r["fuera_de_rango"], 0)
        self.assertFalse(r["requiere_revision"])

    def test_clave_primaria_debe_estar_en_columnas(self):
        """DADO clave_primaria fuera de columnas ENTONCES rechazo."""
        hoja = dict(PERFIL_VALIDO["hojas"][0], clave_primaria="nope")
        perfil = dict(PERFIL_VALIDO, hojas=[hoja])
        self.assertTrue(any("clave_primaria" in e
                            for e in validar(perfil)))

    def test_total_dentro_del_rango_rechazado(self):
        """DADO una fila de total dentro del rango de datos ENTONCES
        rechazo (los totales se declaran fuera, ADR-014)."""
        hoja = dict(PERFIL_VALIDO["hojas"][0], filas_total=[100])
        perfil = dict(PERFIL_VALIDO, hojas=[hoja])
        self.assertTrue(any("filas_total" in e
                            for e in validar(perfil)))

    def test_tolerancia_debe_ser_positiva(self):
        """DADO tolerancia 0 ENTONCES rechazo (reconciliación)."""
        hoja = dict(PERFIL_VALIDO["hojas"][0], tolerancia=0)
        perfil = dict(PERFIL_VALIDO, hojas=[hoja])
        self.assertTrue(any("tolerancia" in e
                            for e in validar(perfil)))

    def test_hoja_duplicada_rechazada(self):
        """DADO dos hojas con el mismo nombre ENTONCES rechazo."""
        perfil = dict(PERFIL_VALIDO, hojas=[
            PERFIL_VALIDO["hojas"][1], PERFIL_VALIDO["hojas"][1]])
        self.assertTrue(any("duplicado" in e
                            for e in validar(perfil)))


class PruebaCargarGuardarPerfil(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.catalogo = Path(self.tmp.name) / "fuentes.json"
        self.catalogo.write_text(
            json.dumps({"version": 1, "fuentes": []}),
            encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_roundtrip_atomico(self):
        """DADO un perfil válido CUANDO se guarda y carga ENTONCES el
        contenido es idéntico al validado."""
        ruta = ruta_perfil(self.catalogo, "fuente-prueba")
        guardar(ruta, PERFIL_VALIDO)
        self.assertEqual(cargar(ruta), PERFIL_VALIDO)

    def test_carga_inexistente_devuelve_none(self):
        """DADO un perfil inexistente CUANDO se carga ENTONCES None
        (sin excepción: E-NOEXISTE lo decide el llamador)."""
        self.assertIsNone(
            cargar(ruta_perfil(self.catalogo, "otra-fuente")))

    def test_carga_corrupta_falla_cerrada(self):
        """DADO JSON inválido CUANDO se carga ENTONCES ErrorPerfil,
        nunca contenido a medias."""
        ruta = ruta_perfil(self.catalogo, "fuente-prueba")
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text("{no-json", encoding="utf-8")
        with self.assertRaises(ErrorPerfil):
            cargar(ruta)

    def test_carga_perfil_invalido_falla_cerrada(self):
        """DADO un perfil que viola el contrato CUANDO se carga
        ENTONCES ErrorPerfil con el campo y el motivo."""
        ruta = ruta_perfil(self.catalogo, "fuente-prueba")
        guardar(ruta, dict(PERFIL_VALIDO, version_perfil=0))
        with self.assertRaises(ErrorPerfil) as ctx:
            cargar(ruta)
        self.assertIn("version_perfil", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
