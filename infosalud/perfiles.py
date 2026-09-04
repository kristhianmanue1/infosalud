"""Perfil estructural de una fuente (ADR-014 fase 1, SPEC-11).

CONTRATO perfil-de-fuente v1: declaración versionada, por hoja, de
dónde están los encabezados, dónde empiezan y terminan los datos y
qué filas son totales (data/perfiles/<id>.json). La normalización
futura (endpoint /datos) consume este perfil: los totales se
separan, no se eliminan, y lo que está fuera del rango declarado no
entra al dato. Validación en la frontera, esquema cerrado,
escritura atómica. La procedencia es obligatoria (huella_base).
"""

import json
import os
import re
from datetime import date
from pathlib import Path

TIPOS_HOJA = {"datos", "descriptiva", "totales", "otra"}
CAMPOS_PERFIL = {"id", "huella_base", "fecha", "version_perfil",
                 "hojas", "notas"}
CAMPOS_HOJA = {"nombre", "tipo", "fila_encabezados",
               "fila_encabezados_sub", "columnas",
               "filas_datos", "clave_primaria", "claves_foraneas",
               "columnas_numericas", "filas_total", "filas_nota",
               "tolerancia"}


class ErrorPerfil(Exception):
    """El perfil no existe o viola el contrato."""


def ruta_perfil(ruta_catalogo, id_fuente):
    """Ruta del perfil de una fuente, junto al catálogo."""
    return (Path(ruta_catalogo).parent / "perfiles"
            / f"{id_fuente}.json")


def cargar(ruta):
    """Devuelve el perfil validado, o None si no existe.

    Lanza ErrorPerfil si existe pero es JSON inválido o viola el
    contrato (fail-closed, nunca contenido a medias).
    """
    ruta = Path(ruta)
    if not ruta.is_file():
        return None
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ErrorPerfil(
            f"perfil corrupto (JSON inválido): {ruta}: {exc}") from exc
    errores = validar(datos)
    if errores:
        raise ErrorPerfil(f"perfil inválido: {'; '.join(errores)}")
    return datos


def guardar(ruta, perfil):
    """Escribe el perfil atómicamente (temporal + rename)."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_name(ruta.name + ".tmp")
    temporal.write_text(
        json.dumps(perfil, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    os.replace(temporal, ruta)


def validar(perfil):
    """Devuelve la lista de errores "campo: motivo" (vacía si vale)."""
    if not isinstance(perfil, dict):
        return ["perfil: se esperaba un objeto JSON"]
    errores = []
    for clave in perfil:
        if clave not in CAMPOS_PERFIL:
            errores.append(
                f"{clave}: campo no declarado (esquema cerrado)")
    id_fuente = perfil.get("id")
    if not isinstance(id_fuente, str) or not re.fullmatch(
            r"[a-z0-9-]+", id_fuente):
        errores.append("id: falta o no cumple el patrón ^[a-z0-9-]+$")
    huella = perfil.get("huella_base")
    if not isinstance(huella, str) or not re.fullmatch(
            r"[0-9a-f]{64}", huella):
        errores.append(
            "huella_base: falta o no es sha256 hex (procedencia "
            "obligatoria, ADR-014)")
    fecha = perfil.get("fecha")
    try:
        date.fromisoformat(fecha)
    except (TypeError, ValueError):
        errores.append(f"fecha: no es ISO-8601: {fecha!r}")
    version = perfil.get("version_perfil")
    if not isinstance(version, int) or isinstance(version, bool) \
            or version < 1:
        errores.append("version_perfil: falta o no es entero >= 1")
    hojas = perfil.get("hojas")
    if not isinstance(hojas, list) or not hojas:
        errores.append("hojas: falta (lista con al menos una hoja)")
    else:
        errores.extend(_validar_hojas(hojas))
    notas = perfil.get("notas")
    if notas is not None and (
            not isinstance(notas, str) or len(notas) > 500):
        errores.append("notas: excede 500 caracteres")
    return errores


def _validar_hojas(hojas):
    """Valida cada hoja del perfil contra el contrato (cerrado)."""
    errores = []
    nombres = set()
    for posicion, hoja in enumerate(hojas):
        prefijo = f"hojas[{posicion}]"
        if not isinstance(hoja, dict):
            errores.append(f"{prefijo}: se esperaba un objeto")
            continue
        for clave in hoja:
            if clave not in CAMPOS_HOJA:
                errores.append(
                    f"{prefijo}: campo '{clave}' no declarado")
        nombre = hoja.get("nombre")
        if not isinstance(nombre, str) or not 1 <= len(nombre) <= 200:
            errores.append(f"{prefijo}.nombre: falta o excede 1..200")
            continue
        prefijo = f"hojas[{nombre}]"
        if nombre in nombres:
            errores.append(f"{prefijo}: nombre de hoja duplicado")
        nombres.add(nombre)
        tipo = hoja.get("tipo")
        if tipo not in TIPOS_HOJA:
            errores.append(
                f"{prefijo}.tipo: fuera del enum {sorted(TIPOS_HOJA)}")
        errores.extend(_validar_fila_entera(hoja, prefijo))
        columnas = hoja.get("columnas")
        if columnas is not None and (
                not isinstance(columnas, list) or not columnas
                or not all(isinstance(c, str) for c in columnas)):
            errores.append(
                f"{prefijo}.columnas: falta o no es lista de textos")
        if tipo == "datos":
            if not isinstance(columnas, list) or not columnas:
                errores.append(
                    f"{prefijo}: tipo 'datos' exige columnas "
                    "declaradas")
            if not isinstance(hoja.get("filas_datos"), dict):
                errores.append(
                    f"{prefijo}: tipo 'datos' exige filas_datos "
                    "{desde, hasta}")
        errores.extend(_validar_rango(hoja, prefijo, columnas))
        errores.extend(_validar_tolerancia(hoja, prefijo))
    return errores


def _validar_fila_entera(hoja, prefijo):
    """fila_encabezados / fila_encabezados_sub: enteros >= 1
    opcionales (la _sub declara la segunda fila de un encabezado
    compuesto, enmienda 2026-09-04)."""
    errores = []
    for campo in ("fila_encabezados", "fila_encabezados_sub"):
        fila = hoja.get(campo)
        if fila is not None and (
                not isinstance(fila, int) or isinstance(fila, bool)
                or fila < 1):
            errores.append(f"{prefijo}.{campo}: no es entero >= 1")
    sub = hoja.get("fila_encabezados_sub")
    principal = hoja.get("fila_encabezados")
    if sub is not None and principal is not None \
            and isinstance(sub, int) and isinstance(principal, int) \
            and sub <= principal:
        errores.append(
            f"{prefijo}.fila_encabezados_sub: debe ser posterior a "
            "fila_encabezados")
    return errores


def _validar_rango(hoja, prefijo, columnas):
    """filas_datos {desde, hasta}; claves y numéricas dentro de
    columnas; filas de total enteras >= 1 y fuera del rango."""
    errores = []
    rango = hoja.get("filas_datos")
    filas_total = hoja.get("filas_total")
    if rango is not None:
        valido = isinstance(rango, dict) and isinstance(
            rango.get("desde"), int) and isinstance(
            rango.get("hasta"), int) and not isinstance(
            rango.get("desde"), bool) and not isinstance(
            rango.get("hasta"), bool)
        if not valido or rango["desde"] < 1 or \
                rango["hasta"] < rango["desde"]:
            errores.append(
                f"{prefijo}.filas_datos: se esperaba {{desde, hasta}} "
                "enteros con 1 <= desde <= hasta")
    if filas_total is not None and (
            not isinstance(filas_total, list) or not filas_total
            or not all(isinstance(f, int) and not isinstance(f, bool)
                       and f >= 1 for f in filas_total)):
        errores.append(
            f"{prefijo}.filas_total: falta o no es lista de enteros "
            ">= 1")
    elif filas_total and isinstance(rango, dict) and isinstance(
            rango.get("desde"), int):
        if any(rango["desde"] <= f <= rango["hasta"]
               for f in filas_total):
            errores.append(
                f"{prefijo}.filas_total: una fila de total está "
                "dentro del rango de datos (los totales se declaran "
                "FUERA del rango, ADR-014)")
    filas_nota = hoja.get("filas_nota")
    if filas_nota is not None and (
            not isinstance(filas_nota, list) or not filas_nota
            or not all(isinstance(f, int) and not isinstance(f, bool)
                       and f >= 1 for f in filas_nota)):
        errores.append(
            f"{prefijo}.filas_nota: falta o no es lista de enteros "
            ">= 1")
    elif filas_nota and isinstance(rango, dict) and isinstance(
            rango.get("desde"), int):
        if any(rango["desde"] <= f <= rango["hasta"]
               for f in filas_nota):
            errores.append(
                f"{prefijo}.filas_nota: una fila de nota está dentro "
                "del rango de datos (las notas se declaran FUERA del "
                "rango)")
    clave = hoja.get("clave_primaria")
    if clave is not None:
        if not isinstance(clave, str) or not 1 <= len(clave) <= 100:
            errores.append(
                f"{prefijo}.clave_primaria: falta o excede 1..100")
        elif isinstance(columnas, list) and clave not in columnas:
            errores.append(
                f"{prefijo}.clave_primaria: '{clave}' no está en "
                "columnas")
    foraneas = hoja.get("claves_foraneas")
    if foraneas is not None:
        if not isinstance(foraneas, list) or not all(
                isinstance(f, dict)
                and isinstance(f.get("campo"), str)
                and isinstance(f.get("dimension"), str)
                for f in foraneas):
            errores.append(
                f"{prefijo}.claves_foraneas: se esperaba lista de "
                "{campo, dimension}")
        elif isinstance(columnas, list):
            for f in foraneas:
                if f["campo"] not in columnas:
                    errores.append(
                        f"{prefijo}.claves_foraneas: campo "
                        f"'{f['campo']}' no está en columnas")
    numericas = hoja.get("columnas_numericas")
    if numericas is not None:
        if not isinstance(numericas, list) or not all(
                isinstance(c, str) for c in numericas):
            errores.append(
                f"{prefijo}.columnas_numericas: no es lista de textos")
        elif isinstance(columnas, list):
            fuera = [c for c in numericas if c not in columnas]
            if fuera:
                errores.append(
                    f"{prefijo}.columnas_numericas: no declaradas en "
                    f"columnas: {', '.join(fuera)}")
    return errores


def _validar_tolerancia(hoja, prefijo):
    """tolerancia: número > 0 opcional (reconciliación ADR-014)."""
    tolerancia = hoja.get("tolerancia")
    if tolerancia is None:
        return []
    if not isinstance(tolerancia, (int, float)) \
            or isinstance(tolerancia, bool) or tolerancia <= 0:
        return [f"{prefijo}.tolerancia: no es número > 0"]
    return []
