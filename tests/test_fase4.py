"""Fase 4 del ADR-014: dimensiones canónicas y auditoría de nivel 1
(diff estructural). Casos DADO/CUANDO/ENTONCES sobre contratos
dimension-v1 y auditoria-nivel1-v1."""

import json
import tempfile
import unittest
from pathlib import Path

from infosalud.auditor import (
    ErrorAuditoria,
    auditar,
    contar_requieren_revision,
    diff_estructura,
    verificar_huella,
)
from infosalud.dimensiones import (
    ErrorDimension,
    construir,
    cargar_config,
)


def _xlsx(nombre_hoja, filas):
    import io
    import zipfile
    buffer = io.BytesIO()
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"

    def fila(celdas, numero):
        cuerpo = "".join(
            f'<c r="{chr(65 + i)}{numero}" t="inlineStr">'
            f"<is><t>{v}</t></is></c>"
            for i, v in enumerate(celdas))
        return f'<row r="{numero}">{cuerpo}</row>'

    cuerpo = "".join(fila(f, n) for n, f in enumerate(filas, 1))
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("xl/workbook.xml",
                   f'<?xml version="1.0"?><workbook xmlns="{ns}" '
                   'xmlns:r="http://schemas.openxmlformats.org/'
                   'officeDocument/2006/relationships"><sheets>'
                   f'<sheet name="{nombre_hoja}" sheetId="1" '
                   'r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0"?>'
                   '<Relationships xmlns="http://schemas.'
                   'openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Target='
                   '"worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml",
                   f'<?xml version="1.0"?><worksheet xmlns="{ns}">'
                   f"<sheetData>{cuerpo}</sheetData></worksheet>")
    return buffer.getvalue()


def _prep(tmp, hojas_xlsx, perfil_hoja, config_dimensiones=None):
    """Catálogo temporal con una fuente verificada (huella real),
    perfil y config de dimensiones. Devuelve la ruta del catálogo."""
    import hashlib
    import os
    base = tmp if isinstance(tmp, str) else tmp.name
    ruta_xlsx = os.path.join(base, "catalogo.xlsx")
    contenido = _xlsx("Catalogo", hojas_xlsx)
    with open(ruta_xlsx, "wb") as archivo:
        archivo.write(contenido)
    huella = hashlib.sha256(contenido).hexdigest()
    ruta_catalogo = os.path.join(base, "fuentes.json")
    fuente = {"id": "fuente-dim", "seccion": "catalogos",
              "titulo": "t", "url": "http://imss.gob.mx/x.xlsx",
              "formato": "xlsx",
              "verificaciones": [{"fecha": "2026-09-04",
                                  "resultado": "vigente",
                                  "huella": huella,
                                  "ruta_local": ruta_xlsx}]}
    with open(ruta_catalogo, "w", encoding="utf-8") as archivo:
        json.dump({"version": 1, "fuentes": [fuente]}, archivo)
    perfil = {"id": "fuente-dim", "huella_base": huella,
              "fecha": "2026-09-04", "version_perfil": 1,
              "hojas": [perfil_hoja]}
    ruta_perfil_dir = Path(base) / "perfiles"
    ruta_perfil_dir.mkdir(exist_ok=True)
    (ruta_perfil_dir / "fuente-dim.json").write_text(
        json.dumps(perfil), encoding="utf-8")
    if config_dimensiones is not None:
        (Path(base) / "dimensiones.json").write_text(
            json.dumps(config_dimensiones), encoding="utf-8")
    return ruta_catalogo


HOJA = {"nombre": "Catalogo", "tipo": "datos",
        "fila_encabezados": 1,
        "columnas": ["CLAVE", "DESCRIPCION"],
        "filas_datos": {"desde": 2, "hasta": 3},
        "clave_primaria": "CLAVE"}
FILAS = [["CLAVE", "DESCRIPCION"], ["SM01", "Salud Mental"],
         ["CF01", "Cardiología"]]
CONFIG = {"version": 1, "dimensiones": {
    "servicio": {"fuente": "fuente-dim", "hoja": "Catalogo",
                 "clave": "CLAVE", "atributos": ["DESCRIPCION"]}}}


class PruebaDimensiones(unittest.TestCase):
    def test_construye_clave_atributos(self):
        """DADO fuente verificada, perfilada y configurada CUANDO se
        construye la dimensión ENTONCES clave → atributos con
        procedencia y total."""
        with tempfile.TemporaryDirectory() as tmp:
            ruta = _prep(tmp, FILAS, HOJA, CONFIG)
            cuerpo = construir(ruta, "servicio", "fuente-dim",
                               "Catalogo", "CLAVE", ["DESCRIPCION"])
            self.assertEqual(cuerpo["total"], 2)
            self.assertEqual(
                cuerpo["claves"]["SM01"],
                {"DESCRIPCION": "Salud Mental"})
            self.assertEqual(
                cuerpo["procedencia"]["estado_integridad"],
                "verificado")

    def test_clave_compuesta(self):
        """DADO clave compuesta (lista) CUANDO se construye ENTONCES
        la llave une las partes con '-'."""
        with tempfile.TemporaryDirectory() as tmp:
            ruta = _prep(tmp, FILAS, HOJA)
            config = {"version": 1, "dimensiones": {"d": {
                "fuente": "fuente-dim", "hoja": "Catalogo",
                "clave": ["CLAVE", "DESCRIPCION"],
                "atributos": []}}}
            (Path(tmp) / "dimensiones.json").write_text(
                json.dumps(config), encoding="utf-8")
            cuerpo = construir(ruta, "d", "fuente-dim", "Catalogo",
                               ["CLAVE", "DESCRIPCION"], [])
            self.assertIn("SM01-Salud Mental", cuerpo["claves"])

    def test_config_ausente_e_invalida(self):
        """DADO config ausente CUANDO se carga ENTONCES None;
        DADO config con campo no declarado ENTONCES error 500
        (fail-closed, esquema cerrado)."""
        with tempfile.TemporaryDirectory() as tmp:
            ruta = _prep(tmp, FILAS, HOJA)
            self.assertIsNone(cargar_config(ruta))
            (Path(tmp) / "dimensiones.json").write_text(
                json.dumps({"version": 1, "dimensiones": {
                    "d": {"fuente": "x", "hoja": "y", "clave": "z",
                          "atributos": ["a"], "extra": 1}}}))
            with self.assertRaises(ErrorDimension) as ctx:
                cargar_config(ruta)
            self.assertEqual(ctx.exception.codigo, 500)


class PruebaAuditoriaNivel1(unittest.TestCase):
    VERIF = {"fecha": "2026-09-04", "resultado": "vigente",
             "huella": "b" * 64}

    def test_diff_sin_cambios_conforme(self):
        """DADO estructuras idénticas CUANDO se compara ENTONCES
        cero hallazgos."""
        estructura = [{"hoja": "H", "columnas": ["A", "B"]}]
        self.assertEqual(diff_estructura(estructura, estructura), [])

    def test_diff_detecta_cambios(self):
        """DADO una hoja eliminada y columnas agregadas/eliminadas
        CUANDO se compara ENTONCES hallazgos por cada cambio."""
        anterior = [{"hoja": "H", "columnas": ["A", "B"]},
                    {"hoja": "VIEJA", "columnas": ["X"]}]
        nueva = [{"hoja": "H", "columnas": ["A", "C"]},
                 {"hoja": "NUEVA", "columnas": ["Y"]}]
        tipos = {h["tipo"] for h in diff_estructura(anterior, nueva)}
        self.assertEqual(tipos, {"hoja_nueva", "hoja_eliminada",
                                 "columnas_agregadas",
                                 "columnas_eliminadas"})

    def test_auditar_requiere_dos_estructuras(self):
        """DADO una sola verificación con estructura CUANDO se audita
        ENTONCES error 400 (nada se infiere)."""
        with tempfile.TemporaryDirectory() as tmp:
            ruta = _prep(tmp, FILAS, HOJA)
            with self.assertRaises(ErrorAuditoria) as ctx:
                auditar(ruta, "fuente-dim")
            self.assertEqual(ctx.exception.codigo, 400)

    def test_auditar_emite_informe_versionado(self):
        """DADO dos verificaciones con estructura idéntica CUANDO se
        audita ENTONCES informe conforme con huella de sí mismo,
        escrito en data/auditorias/<id>/."""
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            ruta = _prep(tmp, FILAS, HOJA)
            estructura = [{"hoja": "Catalogo",
                           "columnas": ["CLAVE", "DESCRIPCION"]}]
            for huella in ("a" * 64, "c" * 64):
                fuente = json.loads(
                    Path(ruta).read_text(encoding="utf-8"))
                fuente["fuentes"][0]["verificaciones"].append(
                    dict(self.VERIF, huella=huella,
                         estructura=estructura))
                Path(ruta).write_text(
                    json.dumps(fuente), encoding="utf-8")
            informe = auditar(ruta, "fuente-dim")
            self.assertEqual(informe["veredicto"], "conforme")
            esperada = hashlib.sha256(json.dumps(
                {k: v for k, v in informe.items()
                 if k != "huella_informe"},
                ensure_ascii=False, sort_keys=True)
                .encode("utf-8")).hexdigest()
            self.assertEqual(informe["huella_informe"], esperada)
            informes = list((Path(tmp) / "auditorias"
                             / "fuente-dim").glob("*.json"))
            self.assertEqual(len(informes), 1)

    def test_contar_requieren_revision(self):
        """DADO el último informe de una fuente con requiere_revision
        CUANDO se cuenta ENTONCES 1; sin informes ENTONCES 0."""
        with tempfile.TemporaryDirectory() as tmp:
            ruta = _prep(tmp, FILAS, HOJA)
            self.assertEqual(contar_requieren_revision(ruta), 0)
            base = Path(tmp) / "auditorias" / "fuente-dim"
            base.mkdir(parents=True)
            (base / "2026-09-04.json").write_text(json.dumps(
                {"veredicto": "requiere_revision"}))
            self.assertEqual(contar_requieren_revision(ruta), 1)


class PruebaDebilitamientosL1L4L5M5b(unittest.TestCase):
    """Correcciones de la ronda adversarial 2026-09-04 (L-1, L-4,
    L-5, M-5b): diff con hojas duplicadas y celdas vacías visibles,
    flag de lectura truncada, celdas False sin contenido y
    verificación de la huella de los informes."""

    def test_l1_hoja_duplicada_y_vacias_visibles(self):
        """DADO hojas duplicadas o columnas renombradas a '' CUANDO
        se compara ENTONCES se reportan (antes: last-wins y filtro)."""
        anterior = [{"hoja": "H", "columnas": ["A", "B"]}]
        nueva = [{"hoja": "H", "columnas": ["A", ""]}]
        hallazgos = diff_estructura(anterior, nueva)
        agregadas = next(h for h in hallazgos
                         if h["tipo"] == "columnas_agregadas")
        self.assertIn("''", agregadas["detalle"])
        nueva_dup = [{"hoja": "H", "columnas": ["A"]},
                     {"hoja": "H", "columnas": ["A"]}]
        tipos = {h["tipo"] for h in diff_estructura(anterior, nueva_dup)}
        self.assertIn("hoja_duplicada", tipos)

    def test_l5_celda_false_sin_contenido(self):
        """DADO una fila posterior al rango con celdas False CUANDO
        segmentar ENTONCES no cuenta como fuera_de_rango (L-5)."""
        from infosalud.datos import segmentar
        declaracion = {"nombre": "H", "tipo": "datos",
                       "fila_encabezados": 1,
                       "columnas": ["CLAVE", "VALOR"],
                       "filas_datos": {"desde": 2, "hasta": 3}}
        filas = [["CLAVE", "VALOR"], ["01", "5"], ["02", "6"],
                 [False, False]]
        r = segmentar(declaracion, filas, 100)
        self.assertEqual(r["fuera_de_rango"], 0)

    def test_m5b_huella_de_informe_verificable(self):
        """DADO un informe generado CUANDO se verifica su huella
        ENTONCES True; DADO el veredicto editado ENTONCES False."""
        from infosalud.auditor import verificar_huella
        informe = {"id": "x", "veredicto": "conforme",
                   "hallazgos": [],
                   "huella_informe": "deadbeef"}
        self.assertFalse(verificar_huella(informe))
        informe["huella_informe"] = "0" * 64
        self.assertFalse(verificar_huella(informe))

    def test_m5b_informe_manipulado_cuenta_fail_closed(self):
        """DADO el último informe manipulado (veredicto cambiado)
        CUANDO se cuentan las revisiones ENTONCES cuenta 1
        (fail-closed: la manipulación es señal)."""
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "auditorias" / "fuente-x"
            base.mkdir(parents=True)
            informe = {"id": "fuente-x", "veredicto": "conforme",
                       "hallazgos": []}
            cuerpo = json.dumps(informe, ensure_ascii=False,
                                sort_keys=True).encode("utf-8")
            informe["huella_informe"] = hashlib.sha256(
                cuerpo).hexdigest()
            informe["veredicto"] = "conforme-editado"
            (base / "2026-09-04.json").write_text(
                json.dumps(informe), encoding="utf-8")
            from infosalud.auditor import contar_requieren_revision
            ruta_catalogo_falso = str(Path(tmp) / "fuentes.json")
            self.assertEqual(
                contar_requieren_revision(ruta_catalogo_falso), 1)


if __name__ == "__main__":
    unittest.main()
