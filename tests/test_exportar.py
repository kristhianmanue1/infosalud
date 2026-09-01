"""SPEC-7 (ADR-011): exportación a CSV y SQLite con evidencia.

Casos DADO/CUANDO/ENTONCES de docs/f1-specs.md SPEC-7 y validación
de los artefactos del sondeo launchd (ADR-008, decisión 8).
"""

import contextlib
import csv
import io
import json
import os
import plistlib
import sqlite3
import subprocess
import tempfile
import unittest
import zipfile

from infosalud.cli import main
from infosalud.exportar import exportar

HUELLA = "b" * 64


def _xlsx_una_hoja():
    buffer = io.BytesIO()
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"

    def fila(celdas, numero):
        cuerpo = "".join(
            f'<c r="{chr(65 + i)}{numero}" t="inlineStr">'
            f"<is><t>{v}</t></is></c>"
            for i, v in enumerate(celdas))
        return f'<row r="{numero}">{cuerpo}</row>'

    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("xl/workbook.xml",
                   f'<?xml version="1.0"?><workbook xmlns="{ns}" '
                   'xmlns:r="http://schemas.openxmlformats.org/'
                   'officeDocument/2006/relationships"><sheets>'
                   '<sheet name="Catalogo" sheetId="1" r:id="rId1"/>'
                   "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0"?>'
                   '<Relationships xmlns="http://schemas.'
                   'openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Target='
                   '"worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml",
                   f'<?xml version="1.0"?><worksheet xmlns="{ns}">'
                   "<sheetData>"
                   + fila(["CLAVE", "Nombre"], 1)
                   + fila(["A001", "FIEBRES"], 2)
                   + "</sheetData></worksheet>")
    return buffer.getvalue()


class PruebaExportacion(unittest.TestCase):
    def setUp(self):
        self.dir_tmp = tempfile.TemporaryDirectory()
        self.origen = os.path.join(self.dir_tmp.name, "f.xlsx")
        with open(self.origen, "wb") as archivo:
            archivo.write(_xlsx_una_hoja())
        self.catalogo = os.path.join(self.dir_tmp.name, "fuentes.json")
        with open(self.catalogo, "w", encoding="utf-8") as archivo:
            json.dump({"version": 1, "fuentes": [{
                "id": "f1", "seccion": "catalogos",
                "titulo": "t", "url": "http://imss.gob.mx/x.xlsx",
                "formato": "xlsx",
                "verificaciones": [{
                    "fecha": "2026-09-01",
                    "resultado": "vigente",
                    "huella": HUELLA,
                    "ruta_local": self.origen,
                }],
            }]}, archivo)

    def tearDown(self):
        self.dir_tmp.cleanup()

    def _main(self, *argv):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            codigo = main([*argv, "--catalogo", self.catalogo])
        return codigo, buffer.getvalue()

    def test_exportacion_csv_con_evidencia(self):
        """DADO xlsx verificado CUANDO se exporta a csv ENTONCES
        hoja→CSV con datos + evidencia.json con huella y fecha."""
        destino = os.path.join(self.dir_tmp.name, "exp_csv")
        codigo, _ = self._main("fuente-exportar", "f1",
                               "--formato", "csv",
                               "--destino", destino)
        self.assertEqual(codigo, 0)
        with open(os.path.join(destino, "f1__Catalogo.csv"),
                  encoding="utf-8-sig") as archivo:
            filas = list(csv.reader(archivo))
        self.assertEqual(filas, [["CLAVE", "Nombre"],
                                 ["A001", "FIEBRES"]])
        with open(os.path.join(destino, "f1__evidencia.json"),
                  encoding="utf-8") as archivo:
            evidencia = json.load(archivo)
        self.assertEqual(evidencia["huella"], HUELLA)
        self.assertEqual(evidencia["fecha"], "2026-09-01")

    def test_exportacion_sqlite_con_tabla_evidencia(self):
        """DADO xlsx verificado CUANDO se exporta a sqlite ENTONCES
        tabla por hoja con datos + tabla evidencia con la huella."""
        destino = os.path.join(self.dir_tmp.name, "exp_sqlite")
        codigo, _ = self._main("fuente-exportar", "f1",
                               "--formato", "sqlite",
                               "--destino", destino)
        self.assertEqual(codigo, 0)
        conexion = sqlite3.connect(
            os.path.join(destino, "f1.sqlite"))
        try:
            tablas = {fila[0] for fila in conexion.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertIn("Catalogo", tablas)
            self.assertIn("evidencia", tablas)
            datos = list(conexion.execute('SELECT * FROM "Catalogo"'))
            self.assertEqual(datos, [("A001", "FIEBRES")])
            evidencia = list(conexion.execute(
                "SELECT fuente, huella FROM evidencia"))
            self.assertEqual(evidencia, [("f1", HUELLA)])
        finally:
            conexion.close()

    def test_destino_existente_rechazado_sin_pisar(self):
        """DADO destino existente ENTONCES salida 1 y productos
        previos intactos."""
        destino = os.path.join(self.dir_tmp.name, "exp")
        self.assertEqual(self._main(
            "fuente-exportar", "f1", "--destino", destino)[0], 0)
        codigo, salida = self._main(
            "fuente-exportar", "f1", "--destino", destino, "--json")
        self.assertEqual(codigo, 1)
        self.assertIn("error", json.loads(salida))
        self.assertTrue(os.path.isfile(
            os.path.join(destino, "f1__Catalogo.csv")))

    def test_sin_archivo_verificado(self):
        """DADO fuente sin verificaciones ENTONCES salida 1."""
        with open(self.catalogo, "w", encoding="utf-8") as archivo:
            json.dump({"version": 1, "fuentes": [{
                "id": "f2", "seccion": "catalogos", "titulo": "t",
                "url": "http://imss.gob.mx/x.xlsx",
                "formato": "xlsx", "verificaciones": [],
            }]}, archivo)
        destino = os.path.join(self.dir_tmp.name, "exp2")
        codigo, _ = self._main(
            "fuente-exportar", "f2", "--destino", destino)
        self.assertEqual(codigo, 1)
        self.assertFalse(os.path.exists(destino))

    def test_sondeo_sintaxis_y_plist_valido(self):
        """DADO artefactos del sondeo ENTONCES el script es bash
        válido y la plantilla launchd parsea como plist."""
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(
            __file__)))
        script = os.path.join(raiz, "scripts", "sondeo.sh")
        r = subprocess.run(["bash", "-n", script],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        ruta_plist = os.path.join(
            raiz, "docs", "launchd",
            "mx.imss.infosalud.sondeo.plist")
        with open(ruta_plist, "rb") as archivo:
            plist = plistlib.load(archivo)
        self.assertEqual(plist["Label"], "mx.imss.infosalud.sondeo")
        self.assertEqual(plist["StartCalendarInterval"]["Day"], 1)


if __name__ == "__main__":
    unittest.main()
