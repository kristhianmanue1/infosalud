"""Nivel 2 de datos normalizados (ADR-014 fase 2, SPEC-12).

Construye la respuesta de `/fuentes/{id}/datos`: filas del archivo
verificado segmentadas por el perfil estructural cuando existe
(datos y totales aparte, fuera_de_rango contado) o filas crudas con
`perfil_aplicado: false` cuando no. El ETag es COMPUESTO
(huella del archivo + sello del perfil + forma de respuesta):
la huella sola sólo sirve para `/archivo` (corrección adversarial
2026-09-03 #1). Sólo stdlib; sin red.
"""

import hashlib
import json

from infosalud.estructura import ErrorEstructura, leer_filas
from infosalud.exportar import MAX_FILAS

FORMA_DATOS = "datos-v1"
TOP_FILAS_DEFECTO = 20_000


class ErrorDatos(Exception):
    """Fallo de construcción de datos con código HTTP asociado."""

    def __init__(self, codigo, mensaje):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


def construir(ruta_archivo, id_fuente, perfil, procedencia,
              hoja=None, max_filas=None):
    """Devuelve (cuerpo, etag). `perfil` puede ser None (sin perfil
    declarado); `procedencia` trae sha256/estado_integridad/fecha ya
    verificados por el llamador (el servicio). Lanza ErrorDatos."""
    if max_filas is None:
        max_filas = TOP_FILAS_DEFECTO
    if not isinstance(max_filas, int) or isinstance(max_filas, bool) \
            or not 1 <= max_filas <= MAX_FILAS:
        raise ErrorDatos(400, f"max_filas: entero 1..{MAX_FILAS}")
    try:
        hojas_leidas = {h["hoja"]: h["filas"]
                        for h in leer_filas(ruta_archivo,
                                            max_filas=MAX_FILAS)}
    except ErrorEstructura as exc:
        raise ErrorDatos(
            400, f"formato no tabular o xlsx ilegible: {exc}") from exc

    sello_perfil = "sin-perfil"
    perfil_resumen = None
    hojas_respuesta = {}
    sin_perfil = []
    if perfil is not None:
        sello_perfil = hashlib.sha256(json.dumps(
            perfil, sort_keys=True,
            ensure_ascii=False).encode("utf-8")).hexdigest()
        perfil_resumen = {"version_perfil": perfil["version_perfil"],
                          "huella_base": perfil["huella_base"],
                          "fecha": perfil["fecha"]}
        declaradas = {h["nombre"]: h for h in perfil["hojas"]}
        if hoja is not None and hoja not in declaradas:
            raise ErrorDatos(
                404, f"hoja no declarada en el perfil: '{hoja}'")
        for nombre in (list(declaradas) if hoja is None else [hoja]):
            declaracion = declaradas[nombre]
            filas = hojas_leidas.get(nombre, [])
            if declaracion.get("tipo") != "datos":
                hojas_respuesta[nombre] = {"tipo": declaracion["tipo"]}
                continue
            hojas_respuesta[nombre] = segmentar(
                declaracion, filas, max_filas)
        sin_perfil = sorted(set(hojas_leidas) - set(declaradas))
    else:
        if hoja is not None and hoja not in hojas_leidas:
            raise ErrorDatos(404, f"hoja inexistente: '{hoja}'")
        for nombre in (list(hojas_leidas) if hoja is None
                       else [hoja]):
            filas = hojas_leidas[nombre]
            hojas_respuesta[nombre] = {
                "filas": filas[:max_filas],
                "truncado": len(filas) > max_filas}
    etag = calcular_etag(procedencia["sha256"], sello_perfil,
                         hoja, max_filas)
    cuerpo = {
        "id": id_fuente,
        "contrato": FORMA_DATOS,
        "perfil": perfil_resumen,
        "perfil_aplicado": perfil is not None,
        "hojas_sin_perfil": sin_perfil,
        "procedencia": procedencia,
        "hojas": hojas_respuesta,
        "etag": etag,
    }
    return cuerpo, etag


def segmentar(declaracion, filas, max_filas):
    """Aplica el rango declarado: los totales van aparte (separación,
    no eliminación). `fuera_de_rango` cuenta filas con contenido
    DESPUÉS del rango (hasta) no declaradas como totales — el caso
    adversarial #4: el portal publica filas nuevas y el perfil viejo
    las recortaría sin avisar. n > 0 → requiere_revision."""
    rango = declaracion["filas_datos"]
    desde, hasta = rango["desde"], rango["hasta"]
    totales_declarados = declaracion.get("filas_total") or []
    datos = filas[desde - 1:hasta]
    fila_enc = declaracion.get("fila_encabezados")
    fuera = [i for i in range(hasta + 1, len(filas) + 1)
             if i not in totales_declarados
             and any(c not in ("", None) for c in filas[i - 1])]
    return {
        "tipo": "datos",
        "fila_encabezados": fila_enc,
        "columnas": declaracion.get("columnas"),
        "filas_datos": {"desde": desde, "hasta": hasta},
        "encabezados": (filas[fila_enc - 1]
                        if fila_enc and fila_enc <= len(filas)
                        else None),
        "datos": datos[:max_filas],
        "totales": [filas[t - 1] for t in totales_declarados
                    if 1 <= t <= len(filas)],
        "fuera_de_rango": len(fuera),
        "requiere_revision": bool(fuera),
        "truncado": len(datos) > max_filas,
    }


def calcular_etag(huella, sello_perfil, hoja, max_filas):
    """ETag compuesto (ADR-014): determinista respecto a contenido,
    perfil y forma de respuesta (incluye selección hoja/max_filas)."""
    forma = (f"{FORMA_DATOS};hoja={hoja or '*'};"
             f"max={max_filas or '*'}")
    return '"' + hashlib.sha256((huella + sello_perfil + forma)
                                .encode("utf-8")).hexdigest() + '"'
