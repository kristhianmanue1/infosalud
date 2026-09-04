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
               "tolerancia", "segmentos", "conciliaciones"}
CAMPOS_SEGMENTO = {"nombre", "fila_encabezados",
                   "fila_encabezados_sub", "columnas",
                   "filas_datos", "clave_primaria", "filas_total",
                   "columnas_numericas", "tolerancia",
                   "conciliaciones"}
CAMPOS_CONCILIACION = {"nombre", "filas", "total_fila",
                       "columnas", "tolerancia"}


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
            if hoja.get("segmentos"):
                # Con segmentos, TODO lo tabular vive en cada
                # segmento: aceptarlo a nivel hoja sería aceptar
                # declaraciones que el runtime ignora en silencio
                # (ronda adversarial 2026-09-04, H-3).
                for campo in ("fila_encabezados", "columnas",
                              "filas_datos", "clave_primaria",
                              "columnas_numericas", "filas_total",
                              "filas_nota", "conciliaciones",
                              "tolerancia"):
                    if hoja.get(campo) is not None:
                        errores.append(
                            f"{prefijo}: con 'segmentos', el campo "
                            f"'{campo}' se declara dentro de cada "
                            "segmento, no en la hoja")
                errores.extend(_validar_segmentos(
                    hoja["segmentos"], prefijo))
            else:
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
        if hoja.get("conciliaciones"):
            errores.extend(_validar_conciliaciones(
                hoja, prefijo, columnas or []))
    return errores


def _validar_segmentos(segmentos, prefijo):
    """Valida los segmentos de una hoja multi-bloque (enmienda
    2026-09-04): cada segmento es una tabla con nombre único y las
    mismas reglas de rango/clave/totales que una hoja."""
    errores = []
    if not isinstance(segmentos, list) or len(segmentos) < 2:
        return [f"{prefijo}.segmentos: se esperaba una lista con al "
                "menos dos segmentos (una tabla única no requiere "
                "segmentos)"]
    nombres = set()
    for posicion, segmento in enumerate(segmentos):
        pref = f"{prefijo}.segmentos[{posicion}]"
        if not isinstance(segmento, dict):
            errores.append(f"{pref}: se esperaba un objeto")
            continue
        for campo in segmento:
            if campo not in CAMPOS_SEGMENTO:
                errores.append(
                    f"{pref}: campo '{campo}' no declarado")
        nombre = segmento.get("nombre")
        if not isinstance(nombre, str) or not 1 <= len(nombre) <= 100:
            errores.append(f"{pref}.nombre: falta o excede 1..100")
            continue
        pref = f"{prefijo}.segmentos[{nombre}]"
        if nombre in nombres:
            errores.append(f"{pref}: nombre de segmento duplicado")
        nombres.add(nombre)
        fila_enc = segmento.get("fila_encabezados")
        if not isinstance(fila_enc, int) or isinstance(fila_enc, bool) \
                or fila_enc < 1:
            errores.append(
                f"{pref}.fila_encabezados: falta o no es entero >= 1")
        columnas = segmento.get("columnas")
        if not isinstance(columnas, list) or not columnas \
                or not all(isinstance(c, str) for c in columnas):
            errores.append(
                f"{pref}.columnas: falta o no es lista de textos")
        rango = segmento.get("filas_datos")
        if not isinstance(rango, dict) or not isinstance(
                rango.get("desde"), int) or isinstance(
                rango.get("desde"), bool) or rango.get("desde", 0) < 1 \
                or rango.get("hasta", 0) < rango.get("desde", 1):
            errores.append(
                f"{pref}.filas_datos: se esperaba {{desde, hasta}} "
                "enteros con 1 <= desde <= hasta")
        clave = segmento.get("clave_primaria")
        if clave is not None:
            if not isinstance(clave, str) or not 1 <= len(clave) <= 100:
                errores.append(
                    f"{pref}.clave_primaria: excede 1..100")
            elif isinstance(columnas, list) and clave not in columnas:
                errores.append(
                    f"{pref}.clave_primaria: '{clave}' no está en "
                    "columnas")
        sub = segmento.get("fila_encabezados_sub")
        if sub is not None and (
                not isinstance(sub, int) or isinstance(sub, bool)
                or sub < 1):
            errores.append(
                f"{pref}.fila_encabezados_sub: no es entero >= 1")
        elif sub is not None and isinstance(fila_enc, int) \
                and sub <= fila_enc:
            errores.append(
                f"{pref}.fila_encabezados_sub: debe ser posterior a "
                "fila_encabezados")
        filas_total = segmento.get("filas_total")
        if filas_total is not None:
            if not isinstance(filas_total, list) or not all(
                    isinstance(f, int) and not isinstance(f, bool)
                    and f >= 1 for f in filas_total):
                errores.append(
                    f"{pref}.filas_total: no es lista de enteros >= 1")
            elif isinstance(rango, dict) and isinstance(
                    rango.get("desde"), int):
                if any(rango["desde"] <= f <= rango["hasta"]
                       for f in filas_total):
                    errores.append(
                        f"{pref}.filas_total: una fila de total está "
                        "dentro del rango del segmento (FUERA, "
                        "ADR-014)")
        numericas = segmento.get("columnas_numericas")
        if numericas is not None and isinstance(columnas, list):
            fuera = [c for c in numericas
                     if not isinstance(c, str) or c not in columnas]
            if fuera:
                errores.append(
                    f"{pref}.columnas_numericas: no declaradas en "
                    f"columnas: {', '.join(fuera)}")
        tolerancia = segmento.get("tolerancia")
        if tolerancia is not None and (
                not isinstance(tolerancia, (int, float))
                or isinstance(tolerancia, bool)
                or not 0 < tolerancia <= TOLERANCIA_MAXIMA):
            errores.append(
                f"{pref}.tolerancia: no es número en (0, "
                f"{TOLERANCIA_MAXIMA}]")
        if segmento.get("conciliaciones"):
            errores.extend(_validar_conciliaciones(
                segmento, pref, columnas or []))
    # Orden y no-solapamiento (ronda adversarial 2026-09-04, H-2):
    # los segmentos se declaran en orden de hoja y sus rangos no se
    # cruzan; lo contrario hace que las ventanas de fuera_de_rango
    # degeneren en silencio.
    especificados = [s for s in segmentos if isinstance(s, dict)
                     and isinstance(s.get("fila_encabezados"), int)
                     and isinstance(s.get("filas_datos"), dict)
                     and isinstance(s["filas_datos"].get("desde"), int)
                     and isinstance(s["filas_datos"].get("hasta"), int)]
    for previo, siguiente in zip(especificados, especificados[1:]):
        if siguiente["fila_encabezados"] <= previo["fila_encabezados"]:
            errores.append(
                f"{prefijo}.segmentos: desordenados — '{siguiente.get('nombre')}' "
                "tiene fila_encabezados <= que el segmento anterior")
        if siguiente["filas_datos"]["desde"] <= previo["filas_datos"]["hasta"]:
            errores.append(
                f"{prefijo}.segmentos: solapados — el rango de "
                f"'{siguiente.get('nombre')}' empieza antes de que "
                f"termine '{previo.get('nombre')}'")
    return errores


def _validar_conciliaciones(declaracion, prefijo, columnas):
    """Valida los grupos de conciliación (enmienda 2026-09-04):
    Σ(filas) ≈ total_fila por columna numérica, con semántica de
    agregación explícita (qué filas suman a qué total)."""
    errores = []
    grupos = declaracion.get("conciliaciones")
    if not isinstance(grupos, list) or not grupos:
        return [f"{prefijo}.conciliaciones: falta (lista con al "
                "menos un grupo)"]
    for posicion, grupo in enumerate(grupos):
        pref = f"{prefijo}.conciliaciones[{posicion}]"
        if not isinstance(grupo, dict):
            errores.append(f"{pref}: se esperaba un objeto")
            continue
        for campo in grupo:
            if campo not in CAMPOS_CONCILIACION:
                errores.append(
                    f"{pref}: campo '{campo}' no declarado")
        nombre = grupo.get("nombre")
        if not isinstance(nombre, str) or not 1 <= len(nombre) <= 100:
            errores.append(f"{pref}.nombre: falta o excede 1..100")
        filas = grupo.get("filas")
        if not isinstance(filas, list) or not filas or not all(
                isinstance(f, int) and not isinstance(f, bool)
                and f >= 1 for f in filas):
            errores.append(
                f"{pref}.filas: falta o no es lista de enteros >= 1")
        total_fila = grupo.get("total_fila")
        if not isinstance(total_fila, int) \
                or isinstance(total_fila, bool) or total_fila < 1:
            errores.append(
                f"{pref}.total_fila: falta o no es entero >= 1")
        elif isinstance(filas, list) and total_fila in filas:
            errores.append(
                f"{pref}.total_fila: la fila de total no puede ser "
                "sumando de sí misma")
        columnas_grupo = grupo.get("columnas")
        if columnas_grupo is not None and isinstance(columnas, list):
            fuera = [c for c in columnas_grupo
                     if not isinstance(c, str) or c not in columnas]
            if fuera:
                errores.append(
                    f"{pref}.columnas: no declaradas: "
                    f"{', '.join(fuera)}")
        tolerancia = grupo.get("tolerancia")
        if tolerancia is not None and (
                not isinstance(tolerancia, (int, float))
                or isinstance(tolerancia, bool)
                or not 0 < tolerancia <= TOLERANCIA_MAXIMA):
            errores.append(
                f"{pref}.tolerancia: no es número en (0, "
                f"{TOLERANCIA_MAXIMA}]")
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


TOLERANCIA_MAXIMA = 0.5


def _validar_tolerancia(hoja, prefijo):
    """tolerancia: número > 0 opcional con techo (ronda adversarial
    2026-09-04, L-2: una tolerancia enorme neutraliza la
    conciliación advisory)."""
    tolerancia = hoja.get("tolerancia")
    if tolerancia is None:
        return []
    if not isinstance(tolerancia, (int, float)) \
            or isinstance(tolerancia, bool) or not 0 < tolerancia \
            <= TOLERANCIA_MAXIMA:
        return [f"{prefijo}.tolerancia: no es número en (0, "
                f"{TOLERANCIA_MAXIMA}]"]
    return []
