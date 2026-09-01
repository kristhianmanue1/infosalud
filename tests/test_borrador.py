"""SPEC-6 (ADR-010): borrador asistido del diccionario.

Casos DADO/CUANDO/ENTONCES de docs/f1-specs.md SPEC-6: enriquecimiento
con valores muestreados, sin sobrescribir lo declarado, y extracción
de metadatos de hojas descriptivas.
"""

import contextlib
import io
import json
import os
import tempfile
import unittest
import zipfile

from infosalud.borrador import analizar, enriquecer
from infosalud.cli import main
from infosalud.estructura import leer_filas

HUELLA = "a" * 64


def _xlsx_dos_hojas():
    """Hoja tabular "Datos" + hoja descriptiva "Metadatos"."""
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
                   '<sheet name="Datos" sheetId="1" r:id="rId1"/>'
                   '<sheet name="Metadatos" sheetId="2" r:id="rId2"/>'
                   "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0"?>'
                   '<Relationships xmlns="http://schemas.'
                   'openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Target='
                   '"worksheets/sheet1.xml"/>'
                   '<Relationship Id="rId2" Target='
                   '"worksheets/sheet2.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml",
                   f'<?xml version="1.0"?><worksheet xmlns="{ns}">'
                   "<sheetData>"
                   + fila(["CLAVE", "Vigente"], 1)
                   + fila(["A001", "S"], 2)
                   + fila(["B002", "N"], 3)
                   + fila(["C003", "S"], 4)
                   + "</sheetData></worksheet>")
        z.writestr("xl/worksheets/sheet2.xml",
                   f'<?xml version="1.0"?><worksheet xmlns="{ns}">'
                   "<sheetData>"
                   + fila(["Versión", "09/02/2024"], 1)
                   + fila(["Fuente", "SIMF"], 2)
                   + "</sheetData></worksheet>")
    return buffer.getvalue()


class PruebaBorrador(unittest.TestCase):
    def setUp(self):
        self.dir_tmp = tempfile.TemporaryDirectory()
        self.xlsx = os.path.join(self.dir_tmp.name, "f.xlsx")
        with open(self.xlsx, "wb") as archivo:
            archivo.write(_xlsx_dos_hojas())
        self.hojas = leer_filas(self.xlsx)

    def tearDown(self):
        self.dir_tmp.cleanup()

    def test_hoja_descriptiva_detectada_y_metadatos(self):
        """DADO hoja descriptiva ENTONCES se clasifica como tal y sus
        filas son metadatos etiqueta→contenido."""
        principal, metas = analizar(self.hojas)
        self.assertEqual(principal["hoja"], "Datos")
        self.assertEqual([m["hoja"] for m in metas], ["Metadatos"])
        etiquetas = [l["etiqueta"] for l in metas[0]["metadatos"]]
        self.assertEqual(etiquetas, ["Versión", "Fuente"])
        self.assertIn("09/02/2024",
                      metas[0]["metadatos"][0]["contenido"])

    def test_enriquecer_sin_sobrescribir_declarado(self):
        """DADO campos con y sin valores declarados ENTONCES sólo los
        vacíos se enriquecen; ejemplo y dominio muestreados."""
        campos = [
            {"nombre": "CLAVE", "tipo": "clave",
             "valores": "declarado", "ejemplo": "X"},
            {"nombre": "Vigente", "tipo": "booleano"},
            {"nombre": "Inexistente", "tipo": "otro"},
        ]
        principal, _ = analizar(self.hojas)
        enriquecidos = enriquecer(campos, principal)
        self.assertEqual(enriquecidos, ["Vigente"])
        self.assertEqual(campos[0]["valores"], "declarado")
        vigente = campos[1]
        self.assertEqual(vigente["ejemplo"], "S")
        self.assertIn("S", vigente["valores"])
        self.assertIn("N", vigente["valores"])
        self.assertNotIn("Inexistente", enriquecidos)

    def test_cli_borrador_excluye_archivo_y_requiere_local(self):
        """DADO --archivo con --borrador ENTONCES salida 1; DADO
        fuente sin verificación ENTONCES salida 1."""
        catalogo = os.path.join(self.dir_tmp.name, "fuentes.json")
        with open(catalogo, "w", encoding="utf-8") as archivo:
            json.dump({"version": 1, "fuentes": [{
                "id": "f1", "seccion": "catalogos",
                "titulo": "t", "url": "http://imss.gob.mx/x.xlsx",
                "formato": "xlsx", "verificaciones": [],
            }]}, archivo)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            codigo = main(["fuente-campos", "f1", "--borrador",
                           "--archivo", "x.json",
                           "--catalogo", catalogo])
        self.assertEqual(codigo, 1)
        with contextlib.redirect_stdout(io.StringIO()):
            codigo = main(["fuente-campos", "f1", "--borrador",
                           "--catalogo", catalogo])
        self.assertEqual(codigo, 1)

    def test_cli_borrador_crea_esqueleto_y_enriquece(self):
        """DADO fuente con verificación (huella, ruta, estructura) y
        sin diccionario ENTONCES --borrador crea y enriquece."""
        catalogo = os.path.join(self.dir_tmp.name, "fuentes.json")
        with open(catalogo, "w", encoding="utf-8") as archivo:
            json.dump({"version": 1, "fuentes": [{
                "id": "f1", "seccion": "catalogos",
                "titulo": "t", "url": "http://imss.gob.mx/x.xlsx",
                "formato": "xlsx",
                "verificaciones": [{
                    "fecha": "2026-09-01",
                    "resultado": "vigente",
                    "huella": HUELLA,
                    "ruta_local": self.xlsx,
                    "estructura": [
                        {"hoja": "Datos",
                         "columnas": ["CLAVE", "Vigente"]}],
                }],
            }]}, archivo)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            codigo = main(["fuente-campos", "f1", "--borrador",
                           "--catalogo", catalogo, "--json"])
        self.assertEqual(codigo, 0)
        salida = json.loads(buffer.getvalue())
        self.assertTrue(salida["creado"])
        self.assertEqual(salida["hojas_descriptivas"], ["Metadatos"])
        ruta_dic = os.path.join(self.dir_tmp.name, "diccionarios",
                                "f1.json")
        with open(ruta_dic, encoding="utf-8") as archivo:
            dic = json.load(archivo)
        self.assertEqual(dic["huella_base"], HUELLA)
        por_nombre = {c["nombre"]: c for c in dic["campos"]}
        self.assertEqual(por_nombre["CLAVE"]["ejemplo"], "A001")
        self.assertIn("S", por_nombre["Vigente"]["valores"])
        self.assertIn("Versión",
                      [l["etiqueta"]
                       for m in dic["metadatos"]
                       for l in m["metadatos"]])


if __name__ == "__main__":
    unittest.main()
