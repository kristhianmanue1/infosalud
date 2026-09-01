"""Carga, validación y guardado del catálogo de fuentes.

Esquemas: CONTRATO registro-de-fuente v1 y cli-infosalud v1.1
(docs/f1-contratos.md).
"""

import json
import os
import re
from datetime import date
from pathlib import Path

SECCIONES = {"catalogos"}
FORMATOS = {"xlsx", "xls", "csv", "pdf", "html", "otro"}
PERIODICIDADES = {
    "diaria", "semanal", "mensual", "anual", "eventual", "desconocida",
}
RESULTADOS = {"vigente", "cambiada", "inaccesible"}
CAMPOS_FUENTE = {
    "id", "seccion", "titulo", "url", "url_listado", "formato",
    "periodicidad", "notas", "verificaciones",
}
CAMPOS_VERIFICACION = {"fecha", "resultado", "huella", "ruta_local",
                       "causa", "estructura", "estructura_causa",
                       "url_previa"}


class ErrorCatalogo(Exception):
    """El catálogo no existe o viola el contrato."""


def cargar_catalogo(ruta):
    """Carga data/fuentes.json y valida la envoltura del contrato.

    Devuelve el diccionario {"version": int, "fuentes": list}.
    Lanza ErrorCatalogo ante archivo ausente, JSON inválido o
    envoltura que no cumpla el contrato. Nunca devuelve un catálogo
    parcialmente válido (fail-closed).
    """
    ruta = Path(ruta)
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ErrorCatalogo(f"catálogo inexistente: {ruta}") from exc
    except json.JSONDecodeError as exc:
        raise ErrorCatalogo(f"catálogo corrupto (JSON inválido): {ruta}: {exc}") from exc
    if not isinstance(datos, dict):
        raise ErrorCatalogo("catálogo: se esperaba un objeto JSON")
    version = datos.get("version")
    if not isinstance(version, int):
        raise ErrorCatalogo("catálogo: falta 'version' (entero)")
    fuentes = datos.get("fuentes")
    if not isinstance(fuentes, list):
        raise ErrorCatalogo("catálogo: falta 'fuentes' (lista)")
    for posicion, fuente in enumerate(fuentes):
        if not isinstance(fuente, dict) or not isinstance(
                fuente.get("id"), str):
            raise ErrorCatalogo(
                f"catálogo: registro inválido en la posición {posicion}")
    return datos


def guardar_catalogo(ruta, datos):
    """Escribe el catálogo atómicamente (temporal + rename).

    Garantía de SPEC-3: un fallo a mitad de escritura deja el
    archivo anterior íntegro, nunca un catálogo a medias.
    """
    ruta = Path(ruta)
    temporal = ruta.with_name(ruta.name + ".tmp")
    temporal.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporal, ruta)


def validar_fuente(fuente):
    """Valida un registro contra CONTRATO registro-de-fuente v1.

    Devuelve la lista de errores "campo: motivo" (vacía si es
    válido). Validación en la frontera, una sola vez, esquema
    cerrado: se acepta lo declarado, se rechaza lo demás.
    """
    if not isinstance(fuente, dict):
        return ["fuente: se esperaba un objeto JSON"]
    errores = []
    for clave in fuente:
        if clave not in CAMPOS_FUENTE:
            errores.append(
                f"{clave}: campo no declarado (esquema cerrado)")
    id_fuente = fuente.get("id")
    if not isinstance(id_fuente, str) or not re.fullmatch(
            r"[a-z0-9-]+", id_fuente):
        errores.append("id: falta o no cumple el patrón ^[a-z0-9-]+$")
    if fuente.get("seccion") not in SECCIONES:
        errores.append(
            "seccion: debe ser uno de: " + ", ".join(sorted(SECCIONES)))
    titulo = fuente.get("titulo")
    if not isinstance(titulo, str) or not 1 <= len(titulo) <= 200:
        errores.append("titulo: falta o excede el rango 1..200")
    url = fuente.get("url")
    if not _url_valida(url):
        errores.append("url: falta o su host no está en *.imss.gob.mx")
    url_listado = fuente.get("url_listado")
    if url_listado is not None and not _url_valida(url_listado):
        errores.append("url_listado: su host no está en *.imss.gob.mx")
    if fuente.get("formato") not in FORMATOS:
        errores.append(
            "formato: debe ser uno de: " + ", ".join(sorted(FORMATOS)))
    periodicidad = fuente.get("periodicidad")
    if periodicidad is not None and periodicidad not in PERIODICIDADES:
        errores.append("periodicidad: debe ser uno de: "
                       + ", ".join(sorted(PERIODICIDADES)))
    notas = fuente.get("notas")
    if notas is not None and (
            not isinstance(notas, str) or len(notas) > 500):
        errores.append("notas: excede 500 caracteres")
    if not isinstance(fuente.get("verificaciones"), list):
        errores.append("verificaciones: falta (lista, inicia vacía)")
    elif fuente["verificaciones"]:
        errores.append("verificaciones: debe iniciar vacía en el alta")
    else:
        errores.extend(_validar_verificaciones(
            fuente["verificaciones"]))
    return errores


def _validar_verificaciones(verificaciones):
    """Valida cada entrada del historial contra el contrato (cerrado)."""
    errores = []
    for entrada in verificaciones:
        if not isinstance(entrada, dict):
            errores.append("verificaciones: cada entrada debe ser un objeto")
            continue
        for clave in entrada:
            if clave not in CAMPOS_VERIFICACION:
                errores.append(
                    f"verificaciones: campo '{clave}' no declarado")
        fecha = entrada.get("fecha")
        try:
            date.fromisoformat(fecha)
        except (TypeError, ValueError):
            errores.append(
                f"verificaciones: 'fecha' no es ISO-8601: {fecha!r}")
        if entrada.get("resultado") not in RESULTADOS:
            errores.append("verificaciones: 'resultado' fuera del enum")
        huella = entrada.get("huella")
        if huella is not None and (
                not isinstance(huella, str) or not re.fullmatch(
                    r"[0-9a-f]{64}", huella)):
            errores.append("verificaciones: 'huella' no es sha256 hex")
        estructura = entrada.get("estructura")
        if estructura is not None and (
                not isinstance(estructura, list)
                or not all(isinstance(h, dict) and isinstance(
                    h.get("hoja"), str) and isinstance(
                    h.get("columnas"), list) for h in estructura)):
            errores.append(
                "verificaciones: 'estructura' no es lista de "
                "{hoja, columnas}")
        estructura_causa = entrada.get("estructura_causa")
        if estructura_causa is not None and (
                not isinstance(estructura_causa, str)
                or len(estructura_causa) > 200):
            errores.append(
                "verificaciones: 'estructura_causa' excede 200 caracteres")
        url_previa = entrada.get("url_previa")
        if url_previa is not None and (
                not isinstance(url_previa, str)
                or len(url_previa) > 300):
            errores.append(
                "verificaciones: 'url_previa' excede 300 caracteres")
    return errores


def _url_valida(url):
    if not isinstance(url, str):
        return False
    if not url.startswith(("http://", "https://")):
        return False
    # El host se valida sin puerto: el portal sirve archivos en
    # infosalud.imss.gob.mx:8080 (URL reales observadas 2026-09-01).
    host = url.split("://", 1)[1].split("/", 1)[0].split(":", 1)[0]
    return host == "imss.gob.mx" or host.endswith(".imss.gob.mx")
