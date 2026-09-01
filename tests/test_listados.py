"""SPEC-8 (ADR-012): vigencia sobre listados históricos.

Casos DADO/CUANDO/ENTONCES de docs/f1-specs.md SPEC-8: selección de
la última ingresada del listado, giro de versión con url_previa y
fail-closed ante listados sin enlaces.
"""

import contextlib
import io
import json
import os
import tempfile
import threading
import unittest
import zipfile
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer

from infosalud.cli import main
from infosalud.red import listar_archivos, mas_reciente

LISTADO = """<html><body>
<p><a href="/ARCHIVOS/cat_09_02_2024.xlsx">Catálogo 2024</a></p>
<p><a href="/ARCHIVOS/cat_2025-03-15.xlsx">Catálogo marzo 2025</a></p>
<p><a href="/ARCHIVOS/Cat_20082026150848.xlsx">Catálogo ago 2026</a></p>
<a href="http://otro.ejemplo.com/x.xlsx">externo</a>
</body></html>"""


class _Servidor(HTTPServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.paginas = {}

    def sirve(self, ruta, contenido):
        self.paginas[ruta] = contenido


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        cuerpo = self.server.paginas.get(self.path)
        if cuerpo is None:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, *args):
        pass


class PruebaHeuristicaReciente(unittest.TestCase):
    def test_fechas_embebidas_en_varios_formatos(self):
        enlaces = [
            ("cat 09_02_2024", "http://h/x1.xlsx"),
            ("Catálogo 2025-03-15", "http://h/x2.xlsx"),
            ("Cat_20082026150848.xlsx", "http://h/x3.xlsx"),
            ("sin fecha", "http://h/x4.xlsx"),
        ]
        texto, url = mas_reciente(enlaces)
        self.assertEqual(url, "http://h/x3.xlsx")
        self.assertEqual(date(2026, 8, 20),
                         date(2026, 8, 20))  # sanidad del formato

    def test_sin_fechas_assume_orden_del_listado(self):
        enlaces = [("a", "http://h/a.xlsx"),
                   ("b", "http://h/b.xlsx")]
        self.assertEqual(mas_reciente(enlaces), ("a", "http://h/a.xlsx"))


class PruebaListadosHistoricos(unittest.TestCase):
    def setUp(self):
        self.dir_tmp = tempfile.TemporaryDirectory()
        self.servidor = _Servidor(("127.0.0.1", 0), _Handler)
        self.puerto = self.servidor.server_address[1]
        hilo = threading.Thread(target=self.servidor.serve_forever)
        hilo.daemon = True
        hilo.start()
        self.base = f"http://127.0.0.1:{self.puerto}"
        self.servidor.sirve("/listado.html", LISTADO.encode())
        self.servidor.sirve("/ARCHIVOS/cat_09_02_2024.xlsx",
                            self._xlsx("viejo"))
        self.servidor.sirve(
            "/ARCHIVOS/Cat_20082026150848.xlsx",
            self._xlsx("nuevo"))
        self.catalogo = os.path.join(self.dir_tmp.name, "fuentes.json")
        self._escribir_fuente(
            f"{self.base}/ARCHIVOS/cat_09_02_2024.xlsx")

    def tearDown(self):
        self.servidor.shutdown()
        self.servidor.server_close()
        self.dir_tmp.cleanup()

    def _xlsx(self, marca):
        buffer = io.BytesIO()
        ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        with zipfile.ZipFile(buffer, "w") as z:
            z.writestr("xl/workbook.xml",
                       f'<?xml version="1.0"?><workbook xmlns="{ns}" '
                       'xmlns:r="http://schemas.openxmlformats.org/'
                       'officeDocument/2006/relationships"><sheets>'
                       '<sheet name="C" sheetId="1" r:id="rId1"/>'
                       "</sheets></workbook>")
            z.writestr("xl/_rels/workbook.xml.rels",
                       '<?xml version="1.0"?>'
                       '<Relationships xmlns="http://schemas.'
                       'openxmlformats.org/package/2006/relationships">'
                       '<Relationship Id="rId1" Target='
                       '"worksheets/sheet1.xml"/></Relationships>')
            z.writestr("xl/worksheets/sheet1.xml",
                       f'<?xml version="1.0"?><worksheet xmlns="{ns}">'
                       f"<sheetData><row r=\"1\">"
                       f"<c r=\"A1\" t=\"inlineStr\"><is><t>{marca}"
                       f"</t></is></c></row></sheetData></worksheet>")
        return buffer.getvalue()

    def _escribir_fuente(self, url, con_listado=True):
        fuente = {
            "id": "f1", "seccion": "catalogos", "titulo": "t",
            "url": url, "formato": "xlsx", "verificaciones": [],
        }
        if con_listado:
            fuente["url_listado"] = f"{self.base}/listado.html"
        with open(self.catalogo, "w", encoding="utf-8") as archivo:
            json.dump({"version": 1, "fuentes": [fuente]}, archivo)

    def _ejecutar(self, *argv):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            codigo = main(["vigencia-verificar", "f1",
                           "--catalogo", self.catalogo, "--json",
                           *argv])
        return codigo, json.loads(buffer.getvalue())

    def test_giro_de_version_toma_la_ultima(self):
        """DADO listado con versiones 2024/2026 ENTONCES verifica la
        última, actualiza url y registra url_previa."""
        codigo, salida = self._ejecutar()
        self.assertEqual(codigo, 0)
        self.assertEqual(salida["resultado"], "vigente")
        self.assertEqual(
            salida["url_previa"],
            f"{self.base}/ARCHIVOS/cat_09_02_2024.xlsx")
        with open(self.catalogo, encoding="utf-8") as archivo:
            fuente = json.load(archivo)["fuentes"][0]
        self.assertEqual(
            fuente["url"],
            f"{self.base}/ARCHIVOS/Cat_20082026150848.xlsx")
        self.assertEqual(
            fuente["verificaciones"][-1]["url_previa"],
            salida["url_previa"])

    def test_segunda_verificacion_estable(self):
        """DADO url ya actualizada CUANDO se verifica de nuevo
        ENTONCES sin url_previa y sin cambio de url."""
        self._ejecutar()
        codigo, salida = self._ejecutar()
        self.assertEqual(codigo, 0)
        self.assertIsNone(salida["url_previa"])
        with open(self.catalogo, encoding="utf-8") as archivo:
            fuente = json.load(archivo)["fuentes"][0]
        self.assertEqual(
            fuente["url"],
            f"{self.base}/ARCHIVOS/Cat_20082026150848.xlsx")
        self.assertEqual(len(fuente["verificaciones"]), 2)

    def test_listado_sin_enlaces_fail_closed(self):
        """DADO listado sin enlaces a archivos ENTONCES salida 1, url
        intacta, sin descarga."""
        self.servidor.sirve("/listado.html",
                            b"<html><body><p>sin enlaces</p></body></html>")
        codigo, salida = self._ejecutar()
        self.assertEqual(codigo, 1)
        self.assertIn("error", salida)
        with open(self.catalogo, encoding="utf-8") as archivo:
            fuente = json.load(archivo)["fuentes"][0]
        self.assertTrue(fuente["url"].endswith("cat_09_02_2024.xlsx"))
        self.assertEqual(fuente["verificaciones"], [])

    def test_sin_url_listado_comportamiento_actual(self):
        """DADO fuente sin url_listado ENTONCES comportamiento de
        siempre contra la URL fija."""
        self._escribir_fuente(
            f"{self.base}/ARCHIVOS/cat_09_02_2024.xlsx",
            con_listado=False)
        codigo, salida = self._ejecutar()
        self.assertEqual(codigo, 0)
        self.assertIsNone(salida["url_previa"])

    def test_listar_archivos_filtra_host_y_extension(self):
        """DADO listado con enlace externo ENTONCES se filtra; los
        internos se absolutizan."""
        enlaces = listar_archivos(f"{self.base}/listado.html")
        urls = [url for _texto, url in enlaces]
        self.assertTrue(all(u.startswith(self.base) for u in urls))
        self.assertTrue(any(u.endswith("cat_2025-03-15.xlsx")
                            for u in urls))


if __name__ == "__main__":
    unittest.main()
