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


def _a_numero(valor):
    """Convierte una celda a float (parser numérico tolerante:
    comas de millar, $ y %); None si no es numérica."""
    if isinstance(valor, (int, float)) and \
            not isinstance(valor, bool):
        return float(valor)
    if not isinstance(valor, str):
        return None
    limpio = valor.strip().replace(",", "").replace("$", "")
    limpio = limpio.replace("%", "").strip()
    if not limpio or limpio in {"-", "--"}:
        return None
    try:
        return float(limpio)
    except ValueError:
        return None


def _conciliar(declaracion, filas, datos, filas_total_indices,
               tolerancia):
    """Reconciliación numérica (ADR-014, corrección adversarial #5):
    para cada fila de total declarada y cada columna numérica,
    compara Σ(detalles) contra el total con tolerancia relativa.
    Devuelve el bloque 'conciliacion' o None si no aplica."""
    columnas = declaracion.get("columnas") or []
    numericas = declaracion.get("columnas_numericas") or []
    if not numericas or not filas_total_indices:
        return None
    tolerancia = declaracion.get("tolerancia") or tolerancia
    indices = [(i, c) for i, c in enumerate(columnas)
               if c in numericas]
    filas_reporte = []
    reconciliado = True
    for t in filas_total_indices:
        if not 1 <= t <= len(filas):
            continue
        fila_total = filas[t - 1]
        ok, mal, ejemplos = 0, 0, []
        for indice, columna in indices:
            if indice >= len(fila_total):
                continue
            total = _a_numero(fila_total[indice])
            if total is None:
                continue
            suma = sum(
                v for v in (_a_numero(fila[indice])
                            for fila in datos
                            if indice < len(fila))
                if v is not None)
            cuadra = abs(suma - total) <= tolerancia * max(
                1.0, abs(total))
            if cuadra:
                ok += 1
            else:
                mal += 1
                if len(ejemplos) < 3:
                    ejemplos.append({"columna": columna,
                                     "suma": suma, "total": total})
        filas_reporte.append({
            "fila": t,
            "columnas_conciliadas": ok,
            "columnas_descuadradas": mal,
            **({"ejemplos_descuadre": ejemplos} if ejemplos else {}),
        })
        if mal:
            reconciliado = False
    if not filas_reporte:
        return None
    return {"reconciliado": reconciliado, "tolerancia": tolerancia,
            "filas": filas_reporte}


def _conciliar_grupo(declaracion, filas, grupo, tolerancia):
    """Concilia un grupo declarado: Σ(filas del grupo) ≈ total_fila
    por columna (semántica de agregación explícita, enmienda
    2026-09-04). Devuelve el reporte del grupo o None si no aplica."""
    columnas = declaracion.get("columnas") or []
    objetivo = grupo.get("columnas") \
        or declaracion.get("columnas_numericas") or []
    total_fila = grupo.get("total_fila")
    if not objetivo or not isinstance(total_fila, int) \
            or not 1 <= total_fila <= len(filas):
        return None
    fila_total = filas[total_fila - 1]
    indices = [(i, c) for i, c in enumerate(columnas)
               if c in objetivo]
    ok, mal, ejemplos = 0, 0, []
    for indice, columna in indices:
        if indice >= len(fila_total):
            continue
        total = _a_numero(fila_total[indice])
        if total is None:
            continue
        suma = sum(
            v for v in (_a_numero(filas[f - 1][indice])
                        for f in grupo["filas"]
                        if f - 1 < len(filas)
                        and indice < len(filas[f - 1]))
            if v is not None)
        cuadra = abs(suma - total) <= tolerancia * max(
            1.0, abs(total))
        if cuadra:
            ok += 1
        else:
            mal += 1
            if len(ejemplos) < 3:
                ejemplos.append({"columna": columna,
                                 "suma": suma, "total": total})
    return {"nombre": grupo["nombre"], "fila": total_fila,
            "columnas_conciliadas": ok,
            "columnas_descuadradas": mal,
            **({"ejemplos_descuadre": ejemplos} if ejemplos else {}),
            "reconciliado": mal == 0 and ok > 0}


def segmentar(declaracion, filas, max_filas):
    """Hoja tipo datos: tabla única (campos de hoja) o multi-bloque
    (lista `segmentos`, enmienda 2026-09-04 — cada segmento es una
    tabla independiente con nombre, rango y totales propios)."""
    if declaracion.get("segmentos"):
        segmentos = declaracion["segmentos"]
        resultados = []
        for i, segmento in enumerate(segmentos):
            # Ventana de fuera_de_rango acotada al bloque: termina
            # donde inicia el encabezado del siguiente segmento.
            fuera_hasta = None
            if i + 1 < len(segmentos):
                siguiente = segmentos[i + 1].get("fila_encabezados")
                fuera_hasta = (siguiente - 1
                               if isinstance(siguiente, int)
                               else None)
            resultados.append(_tabla(segmento, filas, max_filas,
                                     nombre=segmento.get("nombre"),
                                     fuera_hasta=fuera_hasta))
        return {"tipo": "datos", "segmentos": resultados}
    return _tabla(declaracion, filas, max_filas)


def _tabla(declaracion, filas, max_filas, nombre=None, fuera_hasta=None):
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
    fila_sub = declaracion.get("fila_encabezados_sub")
    notas_declaradas = declaracion.get("filas_nota") or []
    def _fila(n):
        return filas[n - 1] if n and n <= len(filas) else None

    limite = fuera_hasta if fuera_hasta is not None else len(filas)
    fuera = [i for i in range(hasta + 1, limite + 1)
             if i not in totales_declarados
             and i not in notas_declaradas
             and any(str(c).strip() for c in filas[i - 1]
                     if c is not None)]
    conciliacion = None
    grupos = declaracion.get("conciliaciones") or []
    if grupos:
        # Semántica de agregación explícita: sólo los grupos
        # declarados se concilian (el Σ ciego sobre todas las filas
        # no reproduce totales por nivel).
        conciliacion = {"reconciliado": True, "tolerancia": 0.005,
                        "filas": [], "grupos": []}
        for grupo in grupos:
            reporte = _conciliar_grupo(declaracion, filas, grupo,
                                       0.005)
            if reporte is None:
                continue
            conciliacion["grupos"].append(reporte)
            if not reporte["reconciliado"]:
                conciliacion["reconciliado"] = False
        if not conciliacion["grupos"]:
            conciliacion = None
    elif declaracion.get("filas_total") \
            and declaracion.get("columnas_numericas"):
        conciliacion = _conciliar(declaracion, filas, datos,
                                  totales_declarados, 0.005)
    return {
        "tipo": "datos",
        "fila_encabezados": fila_enc,
        "encabezados": _fila(fila_enc),
        "encabezados_sub": (_fila(fila_sub)
                            if fila_sub else None),
        "columnas": declaracion.get("columnas"),
        "filas_datos": {"desde": desde, "hasta": hasta},
        "datos": datos[:max_filas],
        "totales": [filas[t - 1] for t in totales_declarados
                    if 1 <= t <= len(filas)],
        "fuera_de_rango": len(fuera),
        "requiere_revision": bool(fuera),
        "truncado": len(datos) > max_filas,
        "conciliacion": conciliacion,
        **({"nombre": nombre} if nombre else {}),
    }


def calcular_etag(huella, sello_perfil, hoja, max_filas):
    """ETag compuesto (ADR-014): determinista respecto a contenido,
    perfil y forma de respuesta (incluye selección hoja/max_filas)."""
    forma = (f"{FORMA_DATOS};hoja={hoja or '*'};"
             f"max={max_filas or '*'}")
    return '"' + hashlib.sha256((huella + sello_perfil + forma)
                                .encode("utf-8")).hexdigest() + '"'
