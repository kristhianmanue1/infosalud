"""SPEC-5 (ADR-009): fuente-campos y estructura observada.

Casos DADO/CUANDO/ENTONCES de docs/f1-specs.md SPEC-5: diccionario
de datos declarado y estructura observada del xlsx en la
verificación de vigencia.
"""

import io
import contextlib
import json
import os
import tempfile
import unittest
import zipfile

from infosalud.cli import main
from infosalud.estructura import extraer_estructura

ID = "catalogo-prueba"

DICCIONARIO = {
    "id": ID,
    "descripcion": "Catálogo de prueba con dos columnas.",
    "uso": "La clave se cruza con SIMF por el campo CLAVE.",
    "campos": [
        {"nombre": "CLAVE", "tipo": "clave",
         "descripcion": "Clave única", "obligatorio": True,
         "ejemplo": "A00-B99"},
        {"nombre": "DESCRIP", "tipo": "texto",
         "descripcion": "Descripción"},
    ],
}

XLSX = None  # se construye una sola vez (ver _construir_xlsx)


def _construir_xlsx():
    buffer = io.BytesIO()
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("xl/workbook.xml",
                   f'<?xml version="1.0"?><workbook xmlns="{ns}" '
                   'xmlns:r="http://schemas.openxmlformats.org/'
                   'officeDocument/2006/relationships"><sheets>'
                   '<sheet name="Datos" sheetId="1" r:id="rId1"/>'
                   "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0"?>'
                   '<Relationships xmlns="http://schemas.'
                   'openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Target='
                   '"worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/sharedStrings.xml",
                   f'<?xml version="1.0"?><sst xmlns="{ns}">'
                   "<si><t>CLAVE</t></si><si><t>DESCRIP</t></si></sst>")
        z.writestr("xl/worksheets/sheet1.xml",
                   f'<?xml version="1.0"?><worksheet xmlns="{ns}">'
                   '<sheetData><row r="1">'
                   '<c r="A1" t="s"><v>0</v></c>'
                   '<c r="B1" t="s"><v>1</v></c>'
                   "</row></sheetData></worksheet>")
    return buffer.getvalue()


class PruebaDiccionarioDatos(unittest.TestCase):
    def setUp(self):
        self.dir_tmp = tempfile.TemporaryDirectory()
        self.catalogo = os.path.join(self.dir_tmp.name, "fuentes.json")
        with open(self.catalogo, "w", encoding="utf-8") as archivo:
            json.dump({"version": 1, "fuentes": [{
                "id": ID, "seccion": "catalogos",
                "titulo": "Fuente de prueba",
                "url": "http://infosalud.imss.gob.mx:8080/x.xlsx",
                "formato": "xlsx", "verificaciones": [],
            }]}, archivo)
        self.ruta_dic = os.path.join(
            self.dir_tmp.name, "diccionarios", f"{ID}.json")
        self.json_dic = os.path.join(self.dir_tmp.name, "dic.json")
        with open(self.json_dic, "w", encoding="utf-8") as archivo:
            json.dump(DICCIONARIO, archivo)

    def tearDown(self):
        self.dir_tmp.cleanup()

    def _main(self, *argv):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            codigo = main([*argv, "--catalogo", self.catalogo])
        return codigo, buffer.getvalue()

    def test_alta_y_consulta_de_diccionario(self):
        """DADO un diccionario válido CUANDO se da de alta y se
        consulta ENTONCES la salida lista nombre/tipo/descripción."""
        codigo, _ = self._main(
            "fuente-campos", ID, "--archivo", self.json_dic)
        self.assertEqual(codigo, 0)
        self.assertTrue(os.path.isfile(self.ruta_dic))
        codigo, salida = self._main(
            "fuente-campos", ID, "--json")
        self.assertEqual(codigo, 0)
        datos = json.loads(salida)["diccionario"]
        self.assertEqual(datos["campos"][0]["nombre"], "CLAVE")
        self.assertEqual(datos["uso"], DICCIONARIO["uso"])

    def test_diccionario_invalido_rechazado_sin_archivo(self):
        """DADO tipo fuera del enum ENTONCES salida 1, sin archivo."""
        invalido = {"id": ID, "campos": [{"nombre": "X",
                                          "tipo": "binario"}]}
        with open(self.json_dic, "w", encoding="utf-8") as archivo:
            json.dump(invalido, archivo)
        codigo, _ = self._main(
            "fuente-campos", ID, "--archivo", self.json_dic)
        self.assertEqual(codigo, 1)
        self.assertFalse(os.path.exists(self.ruta_dic))

    def test_id_distinto_rechazado_anti_huerfanos(self):
        """DADO --archivo con id distinto ENTONCES salida 1."""
        otro = dict(DICCIONARIO, id="otra-fuente")
        with open(self.json_dic, "w", encoding="utf-8") as archivo:
            json.dump(otro, archivo)
        codigo, _ = self._main(
            "fuente-campos", ID, "--archivo", self.json_dic)
        self.assertEqual(codigo, 1)
        self.assertFalse(os.path.exists(self.ruta_dic))

    def test_consulta_sin_diccionario_o_sin_fuente(self):
        """DADO fuente sin diccionario ENTONCES salida 2; DADO id
        inexistente ENTONCES salida 2."""
        codigo, _ = self._main("fuente-campos", ID)
        self.assertEqual(codigo, 2)
        codigo, _ = self._main("fuente-campos", "id-fantasma")
        self.assertEqual(codigo, 2)

    def test_estructura_observada_en_verificacion(self):
        """DADO verificación exitosa de un xlsx ENTONCES la
        verificación registra estructura con hojas y columnas."""
        global XLSX
        if XLSX is None:
            XLSX = _construir_xlsx()
        estructura = extraer_estructura_bytes(XLSX)
        self.assertEqual(estructura, [
            {"hoja": "Datos", "columnas": ["CLAVE", "DESCRIP"]}])

    def test_xlsx_corrupto_da_causa_sin_derribar(self):
        """DADO zip sin workbook ENTONCES ErrorEstructura, no otra
        excepción (mejor esfuerzo, nunca derriba al comando)."""
        from infosalud.estructura import ErrorEstructura
        with self.assertRaises(ErrorEstructura):
            extraer_estructura_bytes(b"PK\x05\x06" + b"\x00" * 18)


def extraer_estructura_bytes(contenido):
    import tempfile
    from infosalud.estructura import extraer_estructura
    with tempfile.NamedTemporaryFile(suffix=".xlsx",
                                     delete=False) as archivo:
        archivo.write(contenido)
        ruta = archivo.name
    try:
        return extraer_estructura(ruta)
    finally:
        os.unlink(ruta)


if __name__ == "__main__":
    unittest.main()
