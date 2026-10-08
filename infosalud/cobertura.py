"""Cobertura de la dimensión `unidades` (ADR-016, F3).

GET /dimensiones/unidades/cobertura y herramienta MCP
`cobertura_unidades`: para cada fuente declarada en
data/cobertura-unidades.json (esquema cerrado), compara sus claves
presupuestales —filas de datos del perfil, excluyendo subtotales
XX000000000000 y 000000000000— contra el maestro `unidades`, y
reporta dentro/fuera con la lista explícita de claves fuera. El
cálculo es en vivo sobre archivos verificados; la config se
actualiza deliberadamente con cada corte nuevo (ADR-016, H-5).
Sólo stdlib; sin red.
"""
import json
from pathlib import Path

from infosalud import datos as modulo_datos
from infosalud.dimensiones import (
    ErrorDimension,
    _perfil_de,
    _ruta_verificada,
    cargar_config as cargar_dimensiones,
    construir as construir_dimension,
)

CAMPOS_ENTRADA = {"fuente", "hoja", "columna"}


def ruta_config(ruta_catalogo):
    return Path(ruta_catalogo).parent / "cobertura-unidades.json"


def cargar_config(ruta_catalogo):
    """Config de cobertura o None si no existe; fail-closed si
    existe pero es inválida."""
    ruta = ruta_config(ruta_catalogo)
    if not ruta.is_file():
        return None
    try:
        config = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ErrorDimension(
            500, f"config de cobertura corrupta: {exc}") from exc
    if not isinstance(config, dict) \
            or not isinstance(config.get("fuentes"), list) \
            or not config["fuentes"]:
        raise ErrorDimension(
            500, "config de cobertura inválida: falta 'fuentes' "
                 "(lista con al menos una entrada)")
    for posicion, entrada in enumerate(config["fuentes"]):
        pref = f"fuentes[{posicion}]"
        if not isinstance(entrada, dict):
            raise ErrorDimension(500, f"{pref}: se esperaba objeto")
        for campo in entrada:
            if campo not in CAMPOS_ENTRADA:
                raise ErrorDimension(
                    500, f"{pref}: campo '{campo}' no declarado "
                         "(esquema cerrado)")
        for campo in CAMPOS_ENTRADA:
            if not isinstance(entrada.get(campo), str) \
                    or not entrada[campo]:
                raise ErrorDimension(
                    500, f"{pref}: falta '{campo}'")
    return config


def es_subtotal(valor):
    """Claves presupuestales de subtotal: 000000000000 (Nacional) o
    XX000000000000 (TOTAL OOAD)."""
    v = str(valor).strip()
    return v == "0" * 12 or (len(v) == 12 and v[2:] == "0" * 10)


def construir(ruta_catalogo, nombre_dimension="unidades"):
    """Cuerpo de cobertura: maestro vs claves de cada fuente
    declarada. Lanza ErrorDimension ante problemas del dato."""
    if nombre_dimension != "unidades":
        raise ErrorDimension(
            404, f"sin cobertura implementada para la dimensión "
                 f"'{nombre_dimension}'")
    config = cargar_config(ruta_catalogo)
    if config is None:
        raise ErrorDimension(
            404, "sin configuración de cobertura "
                 "(data/cobertura-unidades.json)")
    dim_config = cargar_dimensiones(ruta_catalogo)
    if dim_config is None:
        raise ErrorDimension(
            404, "sin configuración de dimensiones "
                 "(data/dimensiones.json)")
    spec = dim_config["dimensiones"].get(nombre_dimension)
    if spec is None:
        raise ErrorDimension(
            404, f"la dimensión '{nombre_dimension}' no está "
                 "declarada")
    maestro = construir_dimension(
        ruta_catalogo, nombre_dimension, spec["fuente"],
        spec["hoja"], spec["clave"], spec["atributos"])
    maestro_claves = set(maestro["claves"])
    filas = []
    for entrada in config["fuentes"]:
        cuerpo, _ = modulo_datos.construir(
            _ruta_verificada(ruta_catalogo, entrada["fuente"]),
            entrada["fuente"],
            _perfil_de(ruta_catalogo, entrada["fuente"]),
            _procedencia(ruta_catalogo, entrada["fuente"]),
            entrada["hoja"], 200000)
        hoja_datos = cuerpo["hojas"].get(entrada["hoja"], {})
        columnas = hoja_datos.get("columnas") or []
        if entrada["columna"] not in columnas:
            raise ErrorDimension(
                500, f"columna '{entrada['columna']}' no está en "
                f"las columnas del perfil de '{entrada['fuente']}'")
        indice = columnas.index(entrada["columna"])
        claves = set()
        for fila in hoja_datos.get("datos") or []:
            if indice < len(fila) and fila[indice] is not None:
                valor = str(fila[indice]).strip()
                if valor and not es_subtotal(valor):
                    claves.add(valor)
        fuera = sorted(claves - maestro_claves)
        filas.append({
            "fuente": entrada["fuente"],
            "hoja": entrada["hoja"],
            "columna": entrada["columna"],
            "total": len(claves),
            "dentro": len(claves & maestro_claves),
            "fuera": len(fuera),
            "fuera_claves": fuera,
        })
    return {
        "contrato": "cobertura-unidades-v1",
        "dimension": nombre_dimension,
        "maestro": {"fuente": maestro["fuente"],
                    "total": maestro["total"]},
        "procedencia": maestro["procedencia"],
        "fuentes": filas,
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
