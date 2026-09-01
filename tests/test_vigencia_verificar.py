"""SPEC-4 (REQ-6, ADR-008): vigencia-verificar.

Casos DADO/CUANDO/ENTONCES de docs/f1-specs.md SPEC-4, probados
contra un servidor HTTP local (loopback): descarga con evidencia,
fail-closed ante red, timeout, contenido no reconocido y redirect
externo.
"""

import hashlib
import json
import os
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from infosalud.cli import main
from infosalud.red import ErrorRed, descargar

ID = "catalogo-prueba"
XLSX_A = b"PK\x03\x04" + b"contenido version A" * 10
XLSX_B = b"PK\x03\x04" + b"contenido version B" * 10
HTML = b"<html><body>pagina de error</body></html>"


class _Servidor(HTTPServer):
    """Servidor de prueba con comportamiento configurable."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.contenido = b""
        self.estado = 200
        self.retardo = 0.0
        self.location = None


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        servidor = self.server
        if servidor.retardo:
            time.sleep(servidor.retardo)
        self.send_response(servidor.estado)
        if servidor.location:
            self.send_header("Location", servidor.location)
            self.end_headers()
            return
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(servidor.contenido)))
        self.end_headers()
        self.wfile.write(servidor.contenido)

    def log_message(self, *args):
        pass


class PruebaVigenciaVerificar(unittest.TestCase):
    """SPEC-4: descarga de sólo lectura con evidencia verificable."""

    def setUp(self):
        self.directorio = tempfile.TemporaryDirectory()
        self.servidor = _Servidor(("127.0.0.1", 0), _Handler)
        self.puerto = self.servidor.server_address[1]
        self.hilo = threading.Thread(target=self.servidor.serve_forever)
        self.hilo.daemon = True
        self.hilo.start()
        self.ruta_catalogo = os.path.join(
            self.directorio.name, "fuentes.json")
        self.destino = os.path.join(
            self.directorio.name, "salida", "catalogo.xlsx")
        self._escribir_catalogo(
            f"http://127.0.0.1:{self.puerto}/catalogo.xlsx")

    def tearDown(self):
        self.servidor.shutdown()
        self.servidor.server_close()
        self.directorio.cleanup()

    def _escribir_catalogo(self, url):
        catalogo = {"version": 1, "fuentes": [{
            "id": ID,
            "seccion": "catalogos",
            "titulo": "Fuente de prueba",
            "url": url,
            "formato": "xlsx",
            "verificaciones": [],
        }]}
        with open(self.ruta_catalogo, "w", encoding="utf-8") as archivo:
            json.dump(catalogo, archivo)

    def _ejecutar(self):
        import contextlib
        import io
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            main([
                "vigencia-verificar", ID,
                "--catalogo", self.ruta_catalogo,
                "--destino", self.destino,
                "--json"])
        return json.loads(buffer.getvalue())

    def _historial(self):
        with open(self.ruta_catalogo, encoding="utf-8") as archivo:
            catalogo = json.load(archivo)
        return catalogo["fuentes"][0]["verificaciones"]

    def test_descarga_exitosa_registra_vigente_con_evidencia(self):
        """DADO portal disponible ENTONCES vigente con fecha y huella."""
        self.servidor.contenido = XLSX_A
        salida = self._ejecutar()
        self.assertEqual(salida["resultado"], "vigente")
        self.assertEqual(salida["huella"],
                         hashlib.sha256(XLSX_A).hexdigest())
        self.assertTrue(os.path.isfile(self.destino))
        with open(self.destino, "rb") as archivo:
            self.assertEqual(archivo.read(), XLSX_A)
        historial = self._historial()
        self.assertEqual(len(historial), 1)
        self.assertIn("fecha", historial[0])

    def test_contenido_distinto_registra_cambiada(self):
        """DADO huella previa H CUANDO el portal sirve otro contenido
        ENTONCES el resultado es cambiada."""
        self.servidor.contenido = XLSX_A
        self.assertEqual(self._ejecutar()["resultado"], "vigente")
        self.servidor.contenido = XLSX_B
        salida = self._ejecutar()
        self.assertEqual(salida["resultado"], "cambiada")
        self.assertEqual(len(self._historial()), 2)

    def test_html_para_xlsx_se_rechaza(self):
        """DADO HTTP 200 con HTML para un xlsx ENTONCES inaccesible."""
        self.servidor.contenido = HTML
        salida = self._ejecutar()
        self.assertIn("error", salida)
        self.assertFalse(os.path.exists(self.destino))
        historial = self._historial()
        self.assertEqual(historial[0]["resultado"], "inaccesible")
        self.assertTrue(historial[0].get("causa"))
        self.assertIn("firma", historial[0]["causa"])

    def test_host_sin_conexion_registra_inaccesible(self):
        """DADO el host sin conexión ENTONCES inaccesible con causa."""
        self.servidor.shutdown()
        self.servidor.server_close()
        self.hilo.join(timeout=5)
        salida = self._ejecutar()
        self.assertIn("error", salida)
        historial = self._historial()
        self.assertEqual(historial[0]["resultado"], "inaccesible")
        self.assertTrue(historial[0].get("causa"))

    def test_timeout_declara_fallo(self):
        """DADO respuesta fuera del timeout ENTONCES ErrorRed, sin
        archivo parcial en destino."""
        self.servidor.retardo = 2.0
        with self.assertRaises(ErrorRed):
            descargar(f"http://127.0.0.1:{self.puerto}/catalogo.xlsx",
                      self.destino, "xlsx", timeout=0.3)
        self.assertFalse(os.path.exists(self.destino))
        self.assertFalse(os.path.exists(self.destino + ".tmp"))

    def test_redirect_externo_rechazado(self):
        """DADO redirect a otro host ENTONCES ErrorRed (SSRF-lite)."""
        self.servidor.estado = 301
        self.servidor.location = "http://otro.ejemplo.com/catalogo.xlsx"
        with self.assertRaises(ErrorRed):
            descargar(f"http://127.0.0.1:{self.puerto}/catalogo.xlsx",
                      self.destino, "xlsx")

    def test_id_inexistente_sale_con_2(self):
        """DADO id inexistente ENTONCES salida 2, sin verificaciones."""
        self.servidor.contenido = XLSX_A
        codigo = main([
            "vigencia-verificar", "id-fantasma",
            "--catalogo", self.ruta_catalogo,
            "--destino", self.destino,
            "--json"])
        self.assertEqual(codigo, 2)
        self.assertEqual(self._historial(), [])


if __name__ == "__main__":
    unittest.main()
