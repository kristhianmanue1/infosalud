"""Borrador asistido del diccionario (ADR-010, SPEC-6).

Analiza las filas del archivo local ya verificado de una fuente para
proponer evidencia observada: dominio muestreado y ejemplo por campo,
y el contenido de las hojas descriptivas (p. ej. "Metadatos y
equivalencia" del CIE-10). El sistema propone, el humano valida:
ninguna descripción se genera ni se sobrescribe (ADR-009).
"""

import re

UMBRAL_HOJA_DESCRIPTIVA = 0.7   # ≥70% de encabezados vacíos
MAX_VALORES = 5
MAX_META_LINEAS = 200

_PATRON_DESCRIPTIVA = re.compile(
    r"meta|descrip|nota|equival|instruc|ayuda|glosario|definic",
    re.IGNORECASE)


def analizar(hojas):
    """Clasifica hojas y extrae metadatos de las descriptivas.

    Devuelve (principal, descriptivas): la hoja tabular con más
    columnas y la lista de {hoja, metadatos: [{etiqueta, contenido}]}
    de las hojas descriptivas con contenido.
    """
    normales = [h for h in hojas if not _es_descriptiva(h)]
    descriptivas = [h for h in hojas if _es_descriptiva(h)]
    principal = max(
        normales,
        key=lambda h: len(h["filas"][0]) if h["filas"] else 0,
        default=None)
    metas = []
    for hoja in descriptivas:
        lineas = []
        for fila in hoja["filas"]:
            celdas = [str(c).strip() for c in fila if str(c).strip()]
            if not celdas:
                continue
            lineas.append({"etiqueta": celdas[0][:100],
                           "contenido": " | ".join(celdas[1:])[:500]})
            if len(lineas) >= MAX_META_LINEAS:
                break
        if lineas:
            metas.append({"hoja": hoja["hoja"], "metadatos": lineas})
    return principal, metas


def enriquecer(campos, hoja_principal):
    """Rellena `valores` y `ejemplo` de los campos que no los tienen,
    muestreando la hoja principal. Devuelve los nombres enriquecidos.
    Nunca sobrescribe lo declarado ni las descripciones."""
    if not hoja_principal or not hoja_principal["filas"]:
        return []
    encabezados = [str(c).strip() for c in hoja_principal["filas"][0]]
    datos = hoja_principal["filas"][1:]
    enriquecidos = []
    for campo in campos:
        if campo.get("valores") or campo.get("ejemplo"):
            continue
        nombre = campo.get("nombre")
        if nombre not in encabezados:
            continue
        indice = encabezados.index(nombre)
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
        enriquecidos.append(nombre)
    return enriquecidos


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
