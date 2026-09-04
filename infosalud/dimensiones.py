"""Dimensiones canónicas (ADR-014 fase 4).

Sirve `GET /dimensiones/{nombre}`: clave → atributos, derivado de
una fuente ya verificada y perfilada, según la configuración de
`data/dimensiones.json` (esquema cerrado). Toda dimensión declara
su procedencia (huella del archivo verificado y versión del
perfil). Sólo stdlib; sin red.
"""

import json
from pathlib import Path

from infosalud import datos as modulo_datos
from infosalud.perfiles import ErrorPerfil, cargar as cargar_perfil

CAMPOS_DIMENSION = {"fuente", "hoja", "clave", "atributos"}


class ErrorDimension(Exception):
    """Fallo con código HTTP asociado (contrato servicio v1)."""

    def __init__(self, codigo, mensaje):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


def ruta_config(ruta_catalogo):
    return Path(ruta_catalogo).parent / "dimensiones.json"


def cargar_config(ruta_catalogo):
    """Devuelve la config de dimensiones o None si no existe;
    fail-closed si existe pero es inválida."""
    ruta = ruta_config(ruta_catalogo)
    if not ruta.is_file():
        return None
    try:
        config = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ErrorDimension(
            500, f"config de dimensiones corrupta: {exc}") from exc
    if not isinstance(config, dict) \
            or not isinstance(config.get("dimensiones"), dict):
        raise ErrorDimension(
            500, "config de dimensiones inválida: falta "
                 "'dimensiones' (objeto)")
    for nombre, spec in config["dimensiones"].items():
        if not isinstance(spec, dict):
            raise ErrorDimension(
                500, f"dimension '{nombre}': se esperaba un objeto")
        for campo in spec:
            if campo not in CAMPOS_DIMENSION:
                raise ErrorDimension(
                    500, f"dimension '{nombre}': campo '{campo}' no "
                         "declarado (esquema cerrado)")
        for campo in ("fuente", "hoja"):
            if not isinstance(spec.get(campo), str) or not spec[campo]:
                raise ErrorDimension(
                    500, f"dimension '{nombre}': falta '{campo}'")
        clave = spec.get("clave")
        if not (isinstance(clave, str) and clave) and \
                not (isinstance(clave, list) and clave and all(
                    isinstance(c, str) and c for c in clave)):
            raise ErrorDimension(
                500, f"dimension '{nombre}': 'clave' debe ser un "
                     "nombre de columna o lista (compuesta)")
        if not isinstance(spec.get("atributos"), list) \
                or not spec["atributos"]:
            raise ErrorDimension(
                500, f"dimension '{nombre}': falta 'atributos' "
                     "(lista con al menos uno)")
    return config


def construir(ruta_catalogo, nombre, fuente, hoja, clave, atributos):
    """Construye el cuerpo de la dimensión: clave → atributos, con
    procedencia. `clave` puede ser un nombre de columna o una lista
    (clave compuesta, unida con '-'). Lanza ErrorDimension ante
    problemas del dato."""
    try:
        cuerpo, _etag = modulo_datos.construir(
            _ruta_verificada(ruta_catalogo, fuente), fuente,
            _perfil_de(ruta_catalogo, fuente),
            _procedencia(ruta_catalogo, fuente), hoja, 200000)
    except ErrorDimension:
        raise
    hojas = cuerpo["hojas"]
    if hoja not in hojas or "datos" not in hojas.get(hoja, {}):
        raise ErrorDimension(
            404, f"la hoja '{hoja}' no tiene datos en la fuente "
                 f"'{fuente}' (¿perfil tipo datos?)")
    hoja_datos = hojas[hoja]
    columnas = hoja_datos.get("columnas") or []
    partes_clave = clave if isinstance(clave, list) else [clave]
    for parte in partes_clave:
        if parte not in columnas:
            raise ErrorDimension(
                500, f"clave '{parte}' no está en las columnas del "
                     f"perfil de '{fuente}'")
    indices_clave = [columnas.index(p) for p in partes_clave]
    indices_atributos = [(a, columnas.index(a)) for a in atributos
                         if a in columnas]
    claves, sin_clave = {}, 0
    for fila in hoja_datos["datos"]:
        valores = [fila[i] if i < len(fila) else None
                   for i in indices_clave]
        if any(not isinstance(v, str) or not v.strip()
               for v in valores):
            sin_clave += 1
            continue
        llave = "-".join(valores)
        claves[llave] = {a: (fila[i] if i < len(fila) else None)
                         for a, i in indices_atributos}
    return {
        "dimension": nombre,
        "contrato": "dimension-v1",
        "fuente": fuente,
        "hoja": hoja,
        "clave": partes_clave,
        "atributos": [a for a, _ in indices_atributos],
        "procedencia": cuerpo["procedencia"],
        "perfil_version": (cuerpo["perfil"] or {}).get(
            "version_perfil"),
        "total": len(claves),
        "sin_clave": sin_clave,
        "claves": claves,
    }


def _procedencia(ruta_catalogo, id_fuente):
    from infosalud.servicio import _archivo_meta
    meta = _archivo_meta(ruta_catalogo, id_fuente)
    if meta["estado_integridad"] != "verificado":
        raise ErrorDimension(
            409, "integridad alterada: el sha256 del archivo local "
                 "no coincide con el registrado")
    return {"sha256": meta["sha256"],
            "sha256_registrado": meta["sha256_registrado"],
            "estado_integridad": meta["estado_integridad"],
            "fecha_verificacion": meta["corte"]}


def _ruta_verificada(ruta_catalogo, id_fuente):
    from infosalud.servicio import (
        _cargar_catalogo, _fuente, _verificacion_con_archivo,
        _ruta_confinada)
    catalogo = _cargar_catalogo(ruta_catalogo)
    fuente = _fuente(catalogo, id_fuente)
    verificacion = _verificacion_con_archivo(fuente)
    if verificacion is None:
        raise ErrorDimension(
            404, f"sin archivo local verificado para '{id_fuente}'")
    return _ruta_confinada(ruta_catalogo, verificacion["ruta_local"])


def _perfil_de(ruta_catalogo, id_fuente):
    from infosalud.perfiles import ruta_perfil
    try:
        return cargar_perfil(ruta_perfil(ruta_catalogo, id_fuente))
    except ErrorPerfil as exc:
        raise ErrorDimension(
            500, f"perfil corrupto: {exc}") from exc
