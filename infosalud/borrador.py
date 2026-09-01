"""Borrador asistido del diccionario (ADR-010, SPEC-6).

Analiza las filas del archivo local ya verificado de una fuente para
proponer evidencia observada: dominio muestreado y ejemplo por campo,
y el contenido de las hojas descriptivas (p. ej. "Metadatos y
equivalencia" del CIE-10). El sistema propone, el humano valida:
ninguna descripción se genera ni se sobrescribe (ADR-009).

Muchos catálogos no empiezan en la fila 1: traen título del
documento, portada o filas vacías antes de los encabezados. La
detección de encabezados escanea las primeras filas buscando una
fila tabular plausible (≥2 celdas, ninguna excesivamente larga).
"""

import re

UMBRAL_HOJA_DESCRIPTIVA = 0.7   # ≥70% de encabezados vacíos
MAX_VALORES = 5
MAX_META_LINEAS = 200
MAX_FILA_ENCABEZADOS = 20       # filas a escanear buscando encabezado
MAX_LARGO_ENCABEZADO = 100      # un encabezado no es un párrafo

_PATRON_DESCRIPTIVA = re.compile(
    r"meta|descrip|nota|equival|instruc|ayuda|glosario|definic",
    re.IGNORECASE)


def analizar(hojas, max_fila=MAX_FILA_ENCABEZADOS):
    """Clasifica hojas y extrae metadatos de las descriptivas.

    Devuelve (principal, descriptivas): la hoja tabular con más
    columnas —con su índice de fila de encabezados— y la lista de
    {hoja, metadatos: [{etiqueta, contenido}]} de las hojas
    descriptivas con contenido.
    """
    principales = []
    metas = []
    for hoja in hojas:
        if _PATRON_DESCRIPTIVA.search(hoja.get("hoja", "")):
            lineas = _lineas_metadatos(hoja)
            if lineas:
                metas.append({"hoja": hoja["hoja"],
                              "metadatos": lineas})
            continue
        deteccion = fila_encabezados(hoja, max_fila)
        if deteccion is None:
            lineas = _lineas_metadatos(hoja)
            if lineas:
                metas.append({"hoja": hoja["hoja"],
                              "metadatos": lineas})
            continue
        indice, _columnas = deteccion
        principales.append({"hoja": hoja["hoja"],
                            "filas": hoja["filas"],
                            "indice": indice})
    principal = max(
        principales,
        key=lambda h: len(h["filas"][h["indice"]]),
        default=None)
    return principal, metas


def fila_encabezados(hoja, max_fila=MAX_FILA_ENCABEZADOS):
    """(índice, columnas) de la primera fila con aspecto de
    encabezado tabular, o None si no la hay."""
    for indice, fila in enumerate((hoja.get("filas") or [])[:max_fila]):
        celdas = [str(c).strip() for c in fila]
        utiles = [c for c in celdas if c]
        if len(utiles) >= 2 and max(len(c) for c in utiles) \
                <= MAX_LARGO_ENCABEZADO:
            return indice, utiles
    return None


def enriquecer(campos, hoja_principal):
    """Rellena `valores` y `ejemplo` de los campos que no los tienen,
    muestreando la hoja principal. Devuelve los nombres enriquecidos.
    Nunca sobrescribe lo declarado ni las descripciones."""
    if not hoja_principal or not hoja_principal["filas"]:
        return []
    indice_fila = hoja_principal.get("indice", 0)
    encabezados = {str(c).strip().lower(): i
                   for i, c in enumerate(
                       hoja_principal["filas"][indice_fila])}
    datos = hoja_principal["filas"][indice_fila + 1:]
    enriquecidos = []
    for campo in campos:
        if campo.get("valores") or campo.get("ejemplo"):
            continue
        indice = encabezados.get(str(campo.get("nombre", "")).lower())
        if indice is None:
            continue
        columna = [str(fila[indice]).strip() for fila in datos
                   if indice < len(fila) and str(fila[indice]).strip()]
        if not columna:
            continue
        campo["ejemplo"] = columna[0][:200]
        distintos = []
        for valor in columna:
            if valor not in distintos:
                distintos.append(valor)
            if len(distintos) >= MAX_VALORES:
                break
        campo["valores"] = (
            " | ".join(distintos)
            + (" | ..." if len(distintos) >= MAX_VALORES else ""))[:200]
        enriquecidos.append(campo["nombre"])
    return enriquecidos


def _lineas_metadatos(hoja):
    lineas = []
    for fila in hoja["filas"]:
        celdas = [str(c).strip() for c in fila if str(c).strip()]
        if not celdas:
            continue
        lineas.append({"etiqueta": celdas[0][:100],
                       "contenido": " | ".join(celdas[1:])[:500]})
        if len(lineas) >= MAX_META_LINEAS:
            break
    return lineas


def _es_descriptiva(hoja):
    """Heurística declarada (ADR-010), dos reglas:
    (a) el nombre de la hoja sugiere descripción (metadatos, notas,
    equivalencias, instrucciones...), o
    (b) primera fila con ≥70% de celdas vacías: no es encabezado
    tabular."""
    if _PATRON_DESCRIPTIVA.search(hoja.get("hoja", "")):
        return True
    filas = hoja.get("filas") or []
    if not filas:
        return True
    encabezados = filas[0]
    if not encabezados:
        return True
    vacios = sum(1 for c in encabezados if not str(c).strip())
    return vacios / len(encabezados) >= UMBRAL_HOJA_DESCRIPTIVA
