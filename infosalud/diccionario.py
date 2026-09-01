"""Diccionario de datos de una fuente (ADR-009, SPEC-5).

CONTRATO diccionario-de-fuente v1: documentación esquematizada por
fuente en data/diccionarios/<id>.json. Validación en la frontera,
esquema cerrado, escritura atómica. Nunca altera la máquina de
estados de vigencia.
"""

import json
import os
import re
from datetime import date
from pathlib import Path

TIPOS_CAMPO = {"texto", "numero", "fecha", "clave", "booleano", "otro"}
CAMPOS_DICCIONARIO = {"id", "descripcion", "uso", "huella_base",
                      "fecha", "campos"}
CAMPOS_CAMPO = {"nombre", "tipo", "descripcion", "obligatorio",
                "valores", "ejemplo"}


class ErrorDiccionario(Exception):
    """El diccionario no existe o viola el contrato."""


def ruta_diccionario(ruta_catalogo, id_fuente):
    """Ruta del diccionario de una fuente, junto al catálogo."""
    return (Path(ruta_catalogo).parent / "diccionarios"
            / f"{id_fuente}.json")


def cargar(ruta):
    """Devuelve el diccionario validado, o None si no existe.

    Lanza ErrorDiccionario si existe pero es JSON inválido o viola
    el contrato (fail-closed, nunca contenido a medias).
    """
    ruta = Path(ruta)
    if not ruta.is_file():
        return None
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ErrorDiccionario(
            f"diccionario corrupto (JSON inválido): {ruta}: {exc}") from exc
    errores = validar(datos)
    if errores:
        raise ErrorDiccionario(
            f"diccionario inválido: {'; '.join(errores)}")
    return datos


def guardar(ruta, diccionario):
    """Escribe el diccionario atómicamente (temporal + rename)."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_name(ruta.name + ".tmp")
    temporal.write_text(
        json.dumps(diccionario, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    os.replace(temporal, ruta)


def validar(diccionario):
    """Devuelve la lista de errores "campo: motivo" (vacía si vale)."""
    if not isinstance(diccionario, dict):
        return ["diccionario: se esperaba un objeto JSON"]
    errores = []
    for clave in diccionario:
        if clave not in CAMPOS_DICCIONARIO:
            errores.append(
                f"{clave}: campo no declarado (esquema cerrado)")
    id_fuente = diccionario.get("id")
    if not isinstance(id_fuente, str) or not re.fullmatch(
            r"[a-z0-9-]+", id_fuente):
        errores.append("id: falta o no cumple el patrón ^[a-z0-9-]+$")
    descripcion = diccionario.get("descripcion")
    if descripcion is not None and (
            not isinstance(descripcion, str)
            or not 1 <= len(descripcion) <= 1000):
        errores.append("descripcion: falta o excede el rango 1..1000")
    uso = diccionario.get("uso")
    if uso is not None and (not isinstance(uso, str) or len(uso) > 500):
        errores.append("uso: excede 500 caracteres")
    huella = diccionario.get("huella_base")
    if huella is not None and (
            not isinstance(huella, str) or not re.fullmatch(
                r"[0-9a-f]{64}", huella)):
        errores.append("huella_base: no es sha256 hex")
    fecha = diccionario.get("fecha")
    if fecha is not None:
        try:
            date.fromisoformat(fecha)
        except (TypeError, ValueError):
            errores.append(f"fecha: no es ISO-8601: {fecha!r}")
    campos = diccionario.get("campos")
    if not isinstance(campos, list) or not campos:
        errores.append("campos: falta (lista con al menos un campo)")
    else:
        errores.extend(_validar_campos(campos))
    return errores


def _validar_campos(campos):
    errores = []
    for posicion, campo in enumerate(campos):
        if not isinstance(campo, dict):
            errores.append(f"campos[{posicion}]: se esperaba un objeto")
            continue
        for clave in campo:
            if clave not in CAMPOS_CAMPO:
                errores.append(
                    f"campos[{posicion}]: '{clave}' no declarado")
        nombre = campo.get("nombre")
        if not isinstance(nombre, str) or not 1 <= len(nombre) <= 100:
            errores.append(
                f"campos[{posicion}].nombre: falta o excede 1..100")
        if campo.get("tipo") not in TIPOS_CAMPO:
            errores.append(
                f"campos[{posicion}].tipo: debe ser uno de: "
                + ", ".join(sorted(TIPOS_CAMPO)))
        descripcion = campo.get("descripcion")
        if descripcion is not None and (
                not isinstance(descripcion, str)
                or len(descripcion) > 300):
            errores.append(
                f"campos[{posicion}].descripcion: excede 300 caracteres")
        obligatorio = campo.get("obligatorio")
        if obligatorio is not None and not isinstance(obligatorio, bool):
            errores.append(
                f"campos[{posicion}].obligatorio: debe ser booleano")
        for clave in ("valores", "ejemplo"):
            valor = campo.get(clave)
            if valor is not None and (
                    not isinstance(valor, str) or len(valor) > 200):
                errores.append(
                    f"campos[{posicion}].{clave}: excede 200 caracteres")
    return errores
