"""Lectura mínima de estructura de xlsx (ADR-009, SPEC-5).

Mejor esfuerzo: nombres de hoja y encabezados (primera fila) de un
xlsx, con sólo stdlib (zipfile + XML). Topes declarados: 30 hojas,
200 columnas. Un fallo levanta ErrorEstructura; nunca debe alterar
el estado de vigencia (la extracción es evidencia, no condición de
éxito).
"""

import re
import xml.etree.ElementTree as ET
import zipfile

TOP_HOJAS = 30
TOP_COLUMNAS = 200
_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_NS_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"


class ErrorEstructura(Exception):
    """No se pudo extraer la estructura del xlsx (mejor esfuerzo)."""


def extraer_estructura(ruta):
    """Devuelve [{"hoja": str, "columnas": [str, ...]}, ...]."""
    try:
        with zipfile.ZipFile(ruta) as zip_archivo:
            compartidas = _cadenas_compartidas(zip_archivo)
            hojas = _hojas(zip_archivo)
            resultado = [
                {"hoja": nombre,
                 "columnas": _encabezados(zip_archivo, objetivo,
                                          compartidas)}
                for nombre, objetivo in hojas[:TOP_HOJAS]]
    except (KeyError, OSError, ET.ParseError, ValueError,
            zipfile.BadZipFile) as exc:
        raise ErrorEstructura(f"xlsx ilegible: {exc}") from exc
    if not resultado:
        raise ErrorEstructura("xlsx sin hojas legibles")
    return resultado


def _local(etiqueta):
    return etiqueta.rsplit("}", 1)[-1]


def _cadenas_compartidas(zip_archivo):
    if "xl/sharedStrings.xml" not in zip_archivo.namelist():
        return []
    raiz = ET.fromstring(zip_archivo.read("xl/sharedStrings.xml"))
    return ["".join(nodo.text or "" for nodo in si.iter()
                    if _local(nodo.tag) == "t")
            for si in raiz if _local(si.tag) == "si"]


def _hojas(zip_archivo):
    """[(nombre_hoja, ruta_interna)] según workbook.xml y sus rels."""
    rels = {}
    if "xl/_rels/workbook.xml.rels" in zip_archivo.namelist():
        raiz = ET.fromstring(
            zip_archivo.read("xl/_rels/workbook.xml.rels"))
        for rel in raiz:
            if _local(rel.tag) == "Relationship":
                objetivo = rel.get("Target", "").lstrip("/")
                rels[rel.get("Id")] = (objetivo if objetivo.startswith(
                    "xl/") else "xl/" + objetivo)
    raiz = ET.fromstring(zip_archivo.read("xl/workbook.xml"))
    hojas = []
    for hoja in (n for n in raiz.iter() if _local(n.tag) == "sheet"):
        objetivo = rels.get(hoja.get(_NS_R + "id"))
        if objetivo:
            hojas.append((hoja.get("name", ""), objetivo))
    return hojas


def _encabezados(zip_archivo, objetivo, compartidas):
    raiz = ET.fromstring(zip_archivo.read(objetivo))
    fila = next((n for n in raiz.iter() if _local(n.tag) == "row"),
                None)
    if fila is None:
        return []
    return _celdas_fila(fila, compartidas)


def leer_filas(ruta, max_filas=200):
    """[{hoja, filas: [[str,...]]}] con hasta max_filas filas por
    hoja (mejor esfuerzo, topes declarados). Para el borrador
    asistido (ADR-010): muestreo y hojas descriptivas."""
    try:
        with zipfile.ZipFile(ruta) as zip_archivo:
            compartidas = _cadenas_compartidas(zip_archivo)
            resultado = []
            for nombre, objetivo in _hojas(zip_archivo)[:TOP_HOJAS]:
                raiz = ET.fromstring(zip_archivo.read(objetivo))
                filas = [_celdas_fila(fila, compartidas)
                         for fila in raiz.iter()
                         if _local(fila.tag) == "row"][:max_filas]
                resultado.append({"hoja": nombre, "filas": filas})
    except (KeyError, OSError, ET.ParseError, ValueError,
            zipfile.BadZipFile) as exc:
        raise ErrorEstructura(f"xlsx ilegible: {exc}") from exc
    return resultado


def _celdas_fila(fila, compartidas):
    """Valores de una fila <row> como lista (índice por letra de
    columna; huecos rellenados con "")."""
    celdas = {}
    orden = 0
    for celda in (n for n in fila.iter() if _local(n.tag) == "c"):
        valor = _valor_celda(celda, compartidas)
        indice = _indice_columna(celda.get("r"), orden)
        celdas[indice] = valor
        orden += 1
    if not celdas:
        return []
    ancho = min(max(celdas) + 1, TOP_COLUMNAS)
    return [celdas.get(i, "") for i in range(ancho)]


def _valor_celda(celda, compartidas):
    tipo = celda.get("t", "n")
    if tipo == "s":
        nodo_v = next((n for n in celda if _local(n.tag) == "v"), None)
        if nodo_v is not None and nodo_v.text:
            return compartidas[int(nodo_v.text)]
        return ""
    if tipo == "inlineStr":
        return "".join(nodo.text or "" for nodo in celda.iter()
                       if _local(nodo.tag) == "t")
    nodo_v = next((n for n in celda if _local(n.tag) == "v"), None)
    return (nodo_v.text or "") if nodo_v is not None else ""


def _indice_columna(referencia, orden):
    letras = "".join(ch for ch in (referencia or "") if ch.isalpha())
    if not letras:
        return orden
    indice = 0
    for ch in letras.upper():
        indice = indice * 26 + (ord(ch) - ord("A") + 1)
    return indice - 1
