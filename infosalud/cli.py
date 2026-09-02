"""CLI de Infosalud Nexus.

Contrato: docs/f1-contratos.md (CONTRATO cli-infosalud v1.1).
Comandos: fuente-alta, fuente-lista, fuente-buscar, fuente-detalle,
fuente-campos, vigencia-registrar, vigencia-verificar,
vigencia-historia. Sin --json la salida es texto plano para el
humano; con --json, un objeto JSON por ejecución en stdout (ADR-006).
Códigos: 0 éxito, 1 E-VALID/E-DUPLICADO, 2 E-NOEXISTE. Sin red,
salvo vigencia-verificar (GET de sólo lectura; ADR-008).
"""

import argparse
import json
import os
import sys

from infosalud import __version__
from infosalud.catalogo import (
    ErrorCatalogo,
    cargar_catalogo,
    guardar_catalogo,
    validar_fuente,
)
from infosalud.borrador import analizar, enriquecer
from infosalud.diccionario import (
    ErrorDiccionario,
    cargar as cargar_diccionario,
    guardar as guardar_diccionario,
    ruta_diccionario,
    validar as validar_diccionario,
)
from infosalud.estructura import (
    ErrorEstructura,
    extraer_estructura,
    leer_filas,
)
from infosalud.exportar import exportar as exportar_insumo
from infosalud.red import (
    ErrorRed,
    descargar,
    listar_archivos,
    mas_reciente,
    nombre_desde_url,
)
from infosalud.vigencia import calcular_huella, determinar_resultado, fecha_hoy

DESCARGAS_POR_DEFECTO = "data/descargas"
EXPORTACIONES_POR_DEFECTO = "data/exportaciones"

CATALOGO_POR_DEFECTO = "data/fuentes.json"


class _Parser(argparse.ArgumentParser):
    """Parser que sale con 1 en uso inválido: el contrato reserva el
    código 2 para E-NOEXISTE (hallazgo adversarial HIGH)."""

    def error(self, mensaje):
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {mensaje}\n")


def _construir_parser():
    parser = _Parser(
        prog="infosalud",
        description="Catálogo local de fuentes de Infosalud "
                    "(red sólo en vigencia-verificar; ADR-008).",
    )
    parser.add_argument("--version", action="version",
                        version=f"infosalud {__version__}")
    sub = parser.add_subparsers(dest="comando", required=True)

    def con_catalogo(subparser):
        subparser.add_argument("--catalogo", default=CATALOGO_POR_DEFECTO,
                               help="ruta del catálogo JSON")
        subparser.add_argument("--json", action="store_true",
                               help="salida JSON parseable (ADR-006)")
        return subparser

    p_alta = con_catalogo(sub.add_parser(
        "fuente-alta", help="da de alta una fuente desde un archivo JSON"))
    p_alta.add_argument("--archivo", required=True,
                        help="JSON con el registro conforme al contrato")

    p_lista = con_catalogo(sub.add_parser(
        "fuente-lista", help="lista las fuentes del catálogo"))
    p_lista.add_argument("--seccion", help="filtra por sección")
    p_lista.add_argument("--formato", help="filtra por formato")

    p_buscar = con_catalogo(sub.add_parser(
        "fuente-buscar", help="busca por término en id, título y notas"))
    p_buscar.add_argument("termino")

    p_detalle = con_catalogo(sub.add_parser(
        "fuente-detalle", help="muestra el registro completo de una fuente"))
    p_detalle.add_argument("id")

    p_campos = con_catalogo(sub.add_parser(
        "fuente-campos",
        help="muestra o crea/actualiza el diccionario de datos "
             "de una fuente (ADR-009)"))
    p_campos.add_argument("id")
    p_campos.add_argument(
        "--archivo",
        help="JSON conforme a diccionario-de-fuente v1 para "
             "crear/actualizar")
    p_campos.add_argument(
        "--borrador", action="store_true",
        help="enriquece el diccionario con evidencia observada del "
             "archivo local verificado (ADR-010); excluyente con "
             "--archivo")

    p_vreg = con_catalogo(sub.add_parser(
        "vigencia-registrar",
        help="registra una verificación de vigencia con huella sha256"))
    p_vreg.add_argument("id")
    p_vreg.add_argument("--archivo", required=True,
                        help="archivo local descargado por el humano")

    p_vhis = con_catalogo(sub.add_parser(
        "vigencia-historia",
        help="lista el historial cronológico de verificaciones"))
    p_vhis.add_argument("id")

    p_vver = con_catalogo(sub.add_parser(
        "vigencia-verificar",
        help="descarga la fuente (GET sólo lectura, ADR-008) y "
             "registra la verificación con su evidencia"))
    p_vver.add_argument("id")
    p_vver.add_argument(
        "--destino",
        help="ruta local destino; por defecto "
             f"{DESCARGAS_POR_DEFECTO}/<id>/<archivo>")

    p_exp = con_catalogo(sub.add_parser(
        "fuente-exportar",
        help="exporta el archivo verificado a CSV o SQLite con "
             "evidencia (ADR-011)"))
    p_exp.add_argument("id")
    p_exp.add_argument(
        "--formato", choices=("csv", "sqlite"), default="csv",
        help="formato del producto derivado (por defecto csv)")
    p_exp.add_argument(
        "--destino",
        help=f"directorio destino; por defecto "
             f"{EXPORTACIONES_POR_DEFECTO}/<id>")

    p_servir = sub.add_parser(
        "servir", help="servicio HTTP de lectura para agentes "
                       "(API JSON + MCP; ADR-013, SPEC-9)")
    p_servir.add_argument("--catalogo", default=CATALOGO_POR_DEFECTO,
                          help="ruta del catálogo JSON")
    p_servir.add_argument("--host", default="127.0.0.1",
                          help="interfaz de escucha (por defecto "
                               "127.0.0.1; usar la IP de intranet "
                               "para exposición deliberada)")
    p_servir.add_argument("--puerto", type=int, default=8081,
                          help="puerto de escucha (por defecto 8081)")

    return parser


def main(argv=None):
    args = _construir_parser().parse_args(argv)
    comandos = {
        "fuente-alta": _fuente_alta,
        "fuente-lista": _fuente_lista,
        "fuente-buscar": _fuente_buscar,
        "fuente-detalle": _fuente_detalle,
        "fuente-campos": _fuente_campos,
        "fuente-exportar": _fuente_exportar,
        "vigencia-registrar": _vigencia_registrar,
        "vigencia-verificar": _vigencia_verificar,
        "vigencia-historia": _vigencia_historia,
        "servir": _servir,
    }
    return comandos[args.comando](args)


def _salir(args, mensaje, codigo):
    # Con --json, "un objeto por ejecución" incluye los fallos.
    if getattr(args, "json", False):
        print(json.dumps({"error": mensaje}, ensure_ascii=False))
    print(f"ERROR: {mensaje}", file=sys.stderr)
    return codigo


def _emitir(args, datos, texto):
    if getattr(args, "json", False):
        print(json.dumps(datos, ensure_ascii=False))
    else:
        print(texto)


def _buscar_fuente(catalogo, id_fuente):
    for fuente in catalogo["fuentes"]:
        if fuente.get("id") == id_fuente:
            return fuente
    return None


def _fuente_alta(args):
    try:
        with open(args.archivo, encoding="utf-8") as archivo:
            fuente = json.load(archivo)
    except (OSError, json.JSONDecodeError) as exc:
        return _salir(args, f"archivo de fuente ilegible: {exc}", 1)
    errores = validar_fuente(fuente)
    for error in errores:
        print(f"ERROR: {error}", file=sys.stderr)
    if errores:
        return 1
    try:
        catalogo = cargar_catalogo(args.catalogo)
    except ErrorCatalogo as exc:
        return _salir(args, str(exc), 1)
    if _buscar_fuente(catalogo, fuente["id"]) is not None:
        return _salir(args, f"id: duplicado '{fuente['id']}'", 1)
    catalogo["fuentes"].append(fuente)
    guardar_catalogo(args.catalogo, catalogo)
    _emitir(args, {"alta": "ok", "fuente": fuente},
            f"alta: {fuente['id']}")
    return 0


def _fuente_lista(args):
    try:
        catalogo = cargar_catalogo(args.catalogo)
    except ErrorCatalogo as exc:
        return _salir(args, str(exc), 1)
    fuentes = catalogo["fuentes"]
    if args.seccion:
        fuentes = [f for f in fuentes if f.get("seccion") == args.seccion]
    if args.formato:
        fuentes = [f for f in fuentes if f.get("formato") == args.formato]
    _emitir(args, {"fuentes": fuentes},
            "\n".join(f"{f['id']}\t{f['titulo']}" for f in fuentes)
            + f"\n{len(fuentes)} fuente(s)")
    return 0


def _fuente_buscar(args):
    if not args.termino.strip():
        return _salir(args, "termino: vacío (no declarado en el contrato)", 1)
    try:
        catalogo = cargar_catalogo(args.catalogo)
    except ErrorCatalogo as exc:
        return _salir(args, str(exc), 1)
    termino = args.termino.lower()
    fuentes = [
        f for f in catalogo["fuentes"]
        if termino in (f.get("id", "") + " " + f.get("titulo", "")
                       + " " + f.get("notas", "")).lower()
    ]
    if not fuentes:
        return _salir(args, f"sin resultados para '{args.termino}'", 2)
    _emitir(args, {"fuentes": fuentes},
            "\n".join(f"{f['id']}\t{f['titulo']}" for f in fuentes))
    return 0


def _fuente_detalle(args):
    try:
        catalogo = cargar_catalogo(args.catalogo)
    except ErrorCatalogo as exc:
        return _salir(args, str(exc), 1)
    fuente = _buscar_fuente(catalogo, args.id)
    if fuente is None:
        return _salir(args, f"id inexistente: '{args.id}'", 2)
    _emitir(args, {"fuente": fuente},
            json.dumps(fuente, ensure_ascii=False, indent=2))
    return 0


def _fuente_campos(args):
    """Consulta o alta/actualización del diccionario de datos
    (CONTRATO diccionario-de-fuente v1, ADR-009)."""
    try:
        catalogo = cargar_catalogo(args.catalogo)
    except ErrorCatalogo as exc:
        return _salir(args, str(exc), 1)
    fuente = _buscar_fuente(catalogo, args.id)
    if fuente is None:
        return _salir(args, f"id inexistente: '{args.id}'", 2)
    ruta = ruta_diccionario(args.catalogo, args.id)
    if args.borrador and args.archivo is not None:
        return _salir(args,
                      "--archivo y --borrador son excluyentes", 1)
    if args.borrador:
        return _borrador(args, fuente, ruta)
    if args.archivo is None:
        try:
            diccionario = cargar_diccionario(ruta)
        except ErrorDiccionario as exc:
            return _salir(args, str(exc), 1)
        if diccionario is None:
            return _salir(
                args,
                f"fuente '{args.id}' sin diccionario de datos "
                "(no existe data/diccionarios/<id>.json)", 2)
        _emitir(args, {"id": args.id, "diccionario": diccionario},
                _texto_diccionario(diccionario))
        return 0
    try:
        with open(args.archivo, encoding="utf-8") as archivo:
            diccionario = json.load(archivo)
    except (OSError, json.JSONDecodeError) as exc:
        return _salir(args, f"archivo de diccionario ilegible: {exc}", 1)
    errores = validar_diccionario(diccionario)
    if diccionario.get("id") != args.id:
        errores.append(
            f"id: '{diccionario.get('id')}' difiere del solicitado "
            f"'{args.id}' (anti-huérfanos)")
    for error in errores:
        print(f"ERROR: {error}", file=sys.stderr)
    if errores:
        return 1
    guardar_diccionario(ruta, diccionario)
    _emitir(args, {"guardado": str(ruta),
                   "campos": len(diccionario["campos"])},
            f"diccionario guardado: {ruta} "
            f"({len(diccionario['campos'])} campo(s))")
    return 0


def _texto_diccionario(diccionario):
    lineas = []
    if diccionario.get("descripcion"):
        lineas.append(diccionario["descripcion"])
    if diccionario.get("uso"):
        lineas.append(f"Uso: {diccionario['uso']}")
    if diccionario.get("fecha"):
        lineas.append(f"Levantado: {diccionario['fecha']}")
    lineas.append("nombre\ttipo\tobligatorio\tdescripcion")
    for campo in diccionario["campos"]:
        lineas.append("\t".join((
            campo.get("nombre", ""),
            campo.get("tipo", ""),
            "sí" if campo.get("obligatorio") else "no",
            campo.get("descripcion", ""))))
    muestreados = [c for c in diccionario["campos"]
                   if c.get("valores") or c.get("ejemplo")]
    if muestreados:
        lineas.append("valores / ejemplo (muestreado)")
        for campo in muestreados:
            lineas.append(f"  {campo.get('nombre', '')}: "
                          f"{campo.get('valores', '')} "
                          f"[ej: {campo.get('ejemplo', '')}]")
    for bloque in diccionario.get("metadatos", []):
        lineas.append(f"— hoja descriptiva: {bloque['hoja']} —")
        for linea in bloque["metadatos"]:
            lineas.append(f"{linea['etiqueta']}: {linea['contenido']}")
    return "\n".join(lineas)


def _fuente_exportar(args):
    """Exporta el archivo verificado a CSV/SQLite con evidencia
    (CONTRATO cli-infosalud v1.1, ADR-011)."""
    try:
        catalogo = cargar_catalogo(args.catalogo)
    except ErrorCatalogo as exc:
        return _salir(args, str(exc), 1)
    fuente = _buscar_fuente(catalogo, args.id)
    if fuente is None:
        return _salir(args, f"id inexistente: '{args.id}'", 2)
    verificacion = _ultima_verificacion_util(fuente)
    if verificacion is None:
        return _salir(args, "sin archivo verificado: ejecute "
                      "vigencia-verificar primero", 1)
    ruta_local = verificacion["ruta_local"]
    if not os.path.isfile(ruta_local):
        return _salir(args,
                      f"archivo local no encontrado: {ruta_local}", 1)
    formato_origen = fuente.get("formato", "otro")
    if formato_origen not in ("xlsx", "csv"):
        return _salir(args, f"formato no exportable: {formato_origen} "
                      "(sólo xlsx/csv; ADR-011)", 1)
    destino = args.destino or os.path.join(
        EXPORTACIONES_POR_DEFECTO, args.id, args.formato)
    evidencia = {"id": args.id,
                 "huella": verificacion["huella"],
                 "fecha": verificacion["fecha"]}
    try:
        productos = exportar_insumo(ruta_local, destino, evidencia,
                                    formato_origen, args.formato)
    except (ValueError, OSError, ErrorEstructura) as exc:
        return _salir(args, f"exportación fallida: {exc}", 1)
    _emitir(args, {"id": args.id, "formato": args.formato,
                   "destino": destino, "productos": productos},
            f"exportados {len(productos)} producto(s) a {destino}:\n"
            + "\n".join(f"  {p}" for p in productos))
    return 0


def _borrador(args, fuente, ruta):
    """Enriquece el diccionario con evidencia observada del archivo
    local verificado (ADR-010). Nunca genera descripciones."""
    verificacion = _ultima_verificacion_util(fuente)
    if verificacion is None:
        return _salir(args, "sin archivo verificado: ejecute "
                      "vigencia-verificar primero", 1)
    ruta_local = verificacion.get("ruta_local")
    if not ruta_local or not os.path.isfile(ruta_local):
        return _salir(args,
                      f"archivo local no encontrado: {ruta_local}", 1)
    try:
        diccionario = cargar_diccionario(ruta)
    except ErrorDiccionario as exc:
        return _salir(args, str(exc), 1)
    creado = diccionario is None
    try:
        hojas = leer_filas(ruta_local)
    except ErrorEstructura as exc:
        return _salir(args, f"lectura del archivo local falló: {exc}", 1)
    principal, metas = analizar(hojas)
    if creado:
        diccionario = _esqueleto_de_principal(args.id, principal) \
            or _esqueleto(args.id, verificacion)
        if diccionario is None:
            return _salir(args, "no se detectaron encabezados "
                          "tabulares en el archivo: el diccionario "
                          "de esta fuente requiere levantamiento "
                          "manual", 1)
    enriquecidos = enriquecer(diccionario["campos"], principal)
    if metas:
        diccionario["metadatos"] = metas
    diccionario["huella_base"] = verificacion["huella"]
    diccionario["fecha"] = fecha_hoy()
    errores = validar_diccionario(diccionario)
    if errores:
        return _salir(args, "; ".join(errores), 1)
    guardar_diccionario(ruta, diccionario)
    total_meta = sum(len(m["metadatos"]) for m in metas)
    _emitir(args, {"guardado": str(ruta), "creado": creado,
                   "campos_enriquecidos": enriquecidos,
                   "hojas_descriptivas": [m["hoja"] for m in metas],
                   "lineas_metadatos": total_meta},
            f"borrador: {len(enriquecidos)} campo(s) enriquecido(s), "
            f"{total_meta} línea(s) de metadatos en "
            f"{len(metas)} hoja(s) descriptiva(s) → {ruta}")
    return 0


def _esqueleto_de_principal(id_fuente, principal):
    """Esqueleto desde la hoja principal detectada por borrador
    (encabezados pueden estar en cualquier fila inicial)."""
    if not principal or "indice" not in principal:
        return None
    columnas = [str(c).strip() for c
                in principal["filas"][principal["indice"]]
                if str(c).strip()]
    if len(columnas) < 2:
        return None
    return {"id": id_fuente,
            "campos": [{"nombre": c,
                        "tipo": "clave" if i == 0 else "otro"}
                       for i, c in enumerate(columnas)]}


def _ultima_verificacion_util(fuente):
    for verificacion in reversed(fuente.get("verificaciones", [])):
        if verificacion.get("huella") and verificacion.get("ruta_local"):
            return verificacion
    return None


def _esqueleto(id_fuente, verificacion):
    """Esqueleto de diccionario desde la estructura observada:
    primera hoja CON encabezados (algunos libros abren con hojas
    de portada vacías)."""
    estructura = verificacion.get("estructura")
    if not estructura:
        return None
    for hoja in estructura:
        columnas = [c for c in hoja.get("columnas", []) if c]
        if columnas:
            return {"id": id_fuente,
                    "campos": [{"nombre": c,
                                "tipo": "clave" if i == 0 else "otro"}
                               for i, c in enumerate(columnas)]}
    return None


def _agregar_verificacion(catalogo_ruta, catalogo, fuente, ruta,
                          causa=None, estructura=None,
                          estructura_causa=None, url_previa=None):
    """Calcula la huella de ruta (o registra causa de fallo), agrega
    la verificación al historial y guarda el catálogo atómicamente.
    Devuelve la verificación agregada (inaccesible incluida)."""
    verificacion = {"fecha": fecha_hoy(), "ruta_local": ruta}
    if causa is None:
        try:
            huella = calcular_huella(ruta)
        except OSError as exc:
            # Fallo explícito: se registra inaccesible con su causa,
            # nunca éxito inferido.
            verificacion["resultado"] = "inaccesible"
            verificacion["causa"] = str(exc)[:200]
        else:
            verificacion["resultado"] = determinar_resultado(
                huella, fuente["verificaciones"])
            verificacion["huella"] = huella
    else:
        verificacion["resultado"] = "inaccesible"
        verificacion["causa"] = causa[:200]
    if estructura is not None:
        verificacion["estructura"] = estructura
    if estructura_causa is not None:
        verificacion["estructura_causa"] = estructura_causa[:200]
    if url_previa is not None:
        verificacion["url_previa"] = url_previa[:300]
    fuente["verificaciones"].append(verificacion)
    guardar_catalogo(catalogo_ruta, catalogo)
    return verificacion


def _vigencia_registrar(args):
    try:
        catalogo = cargar_catalogo(args.catalogo)
    except ErrorCatalogo as exc:
        return _salir(args, str(exc), 1)
    fuente = _buscar_fuente(catalogo, args.id)
    if fuente is None:
        return _salir(args, f"id inexistente: '{args.id}'", 2)
    if not isinstance(fuente.get("verificaciones"), list):
        return _salir(
            args,
            f"fuente '{args.id}' sin 'verificaciones' (catálogo inválido)",
            1)
    verificacion = _agregar_verificacion(
        args.catalogo, catalogo, fuente, args.archivo)
    if verificacion["resultado"] == "inaccesible":
        return _salir(
            args, f"archivo ilegible: {verificacion['causa']}", 1)
    _emitir(args, {"id": args.id, "resultado": verificacion["resultado"],
                   "fecha": verificacion["fecha"],
                   "huella": verificacion["huella"]},
            f"{args.id}: {verificacion['resultado']} "
            f"({verificacion['fecha']})")
    return 0


def _vigencia_verificar(args):
    """Descarga la fuente (GET sólo lectura, ADR-008) y registra la
    verificación con evidencia. Fail-closed: todo fallo queda como
    `inaccesible` con causa; nunca éxito inferido."""
    try:
        catalogo = cargar_catalogo(args.catalogo)
    except ErrorCatalogo as exc:
        return _salir(args, str(exc), 1)
    fuente = _buscar_fuente(catalogo, args.id)
    if fuente is None:
        return _salir(args, f"id inexistente: '{args.id}'", 2)
    if not isinstance(fuente.get("verificaciones"), list):
        return _salir(
            args,
            f"fuente '{args.id}' sin 'verificaciones' (catálogo inválido)",
            1)
    if not fuente.get("url"):
        return _salir(args, f"fuente '{args.id}' sin url registrada", 1)
    url = fuente["url"]
    url_previa = None
    if fuente.get("url_listado"):
        try:
            enlaces = listar_archivos(fuente["url_listado"])
        except ErrorRed as exc:
            return _salir(args, f"listado histórico ilegible: {exc}", 1)
        if not enlaces:
            return _salir(args, "listado histórico sin enlaces a "
                          "archivos: no se descarga nada "
                          "(fail-closed, ADR-012)", 1)
        _texto, url_ultima = mas_reciente(enlaces)
        if url_ultima != url:
            url_previa, url = url, url_ultima
    destino = args.destino or _destino_por_defecto(url, args.id)
    try:
        descargar(url, destino, fuente.get("formato", "otro"))
    except (ErrorRed, OSError) as exc:
        verificacion = _agregar_verificacion(
            args.catalogo, catalogo, fuente, destino, causa=str(exc))
        return _salir(args, f"descarga fallida: "
                      f"{verificacion['causa']}", 1)
    if url_previa:
        # Giro de versión (ADR-012): el registro vigila la última
        # ingresada; la anterior queda documentada en url_previa.
        fuente["url"] = url
    verificacion = _agregar_verificacion(
        args.catalogo, catalogo, fuente, destino,
        url_previa=url_previa,
        **_estructura_observada(fuente, destino))
    _emitir(args, {"id": args.id, "resultado": verificacion["resultado"],
                   "fecha": verificacion["fecha"],
                   "huella": verificacion["huella"],
                   "ruta_local": destino,
                   "url_previa": url_previa},
            f"{args.id}: {verificacion['resultado']} "
            f"({verificacion['fecha']}) {destino}"
            + (f" [nueva versión; antes: {url_previa}]"
               if url_previa else ""))
    return 0


def _estructura_observada(fuente, destino):
    """Extracción de mejor esfuerzo (ADR-009): nunca altera la
    vigencia; su fallo sólo deja evidencia en estructura_causa."""
    if fuente.get("formato") != "xlsx":
        return {}
    try:
        return {"estructura": extraer_estructura(destino)}
    except ErrorEstructura as exc:
        return {"estructura_causa": str(exc)}


def _destino_por_defecto(url, id_fuente):
    return os.path.join(DESCARGAS_POR_DEFECTO, id_fuente,
                        nombre_desde_url(url))


def _servir(args):
    """Delega en infosalud.servicio (ADR-013, SPEC-9); el token
    opcional llega por entorno, nunca por argv."""
    from infosalud.servicio import servir
    return servir(args)


def _vigencia_historia(args):
    try:
        catalogo = cargar_catalogo(args.catalogo)
    except ErrorCatalogo as exc:
        return _salir(args, str(exc), 1)
    fuente = _buscar_fuente(catalogo, args.id)
    if fuente is None:
        return _salir(args, f"id inexistente: '{args.id}'", 2)
    verificaciones = fuente.get("verificaciones")
    if not isinstance(verificaciones, list):
        return _salir(
            args,
            f"fuente '{args.id}' sin 'verificaciones' (catálogo inválido)",
            1)
    _emitir(args, {"id": args.id, "verificaciones": verificaciones},
            "\n".join(
                f"{v['fecha']}\t{v['resultado']}\t{v.get('huella', '-')}"
                for v in verificaciones) or "sin verificaciones")
    return 0
