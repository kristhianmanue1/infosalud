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
