"""CLI de Infosalud Nexus.

Contrato: docs/f1-contratos.md (CONTRATO cli-infosalud v1.1).
Comandos: fuente-alta, fuente-lista, fuente-buscar, fuente-detalle,
vigencia-registrar, vigencia-historia. Sin --json la salida es texto
plano para el humano; con --json, un objeto JSON por ejecución en
stdout (ADR-006). Códigos: 0 éxito, 1 E-VALID/E-DUPLICADO, 2
E-NOEXISTE. Sin comunicación de red (ADR-004).
"""

import argparse
import json
import sys

from infosalud import __version__
from infosalud.catalogo import (
    ErrorCatalogo,
    cargar_catalogo,
    guardar_catalogo,
    validar_fuente,
)
from infosalud.vigencia import calcular_huella, determinar_resultado, fecha_hoy

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
        description="Catálogo local de fuentes de Infosalud (sin red).",
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

    return parser


def main(argv=None):
    args = _construir_parser().parse_args(argv)
    comandos = {
        "fuente-alta": _fuente_alta,
        "fuente-lista": _fuente_lista,
        "fuente-buscar": _fuente_buscar,
        "fuente-detalle": _fuente_detalle,
        "vigencia-registrar": _vigencia_registrar,
        "vigencia-historia": _vigencia_historia,
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
    verificacion = {"fecha": fecha_hoy(), "ruta_local": args.archivo}
    try:
        huella = calcular_huella(args.archivo)
    except OSError as exc:
        # Fallo explícito: se registra inaccesible con su causa,
        # nunca éxito inferido.
        verificacion["resultado"] = "inaccesible"
        verificacion["causa"] = str(exc)[:200]
        fuente["verificaciones"].append(verificacion)
        guardar_catalogo(args.catalogo, catalogo)
        return _salir(args, f"archivo ilegible: {exc}", 1)
    verificacion["resultado"] = determinar_resultado(
        huella, fuente["verificaciones"])
    verificacion["huella"] = huella
    fuente["verificaciones"].append(verificacion)
    guardar_catalogo(args.catalogo, catalogo)
    _emitir(args, {"id": args.id, "resultado": verificacion["resultado"],
                   "fecha": verificacion["fecha"], "huella": huella},
            f"{args.id}: {verificacion['resultado']} "
            f"({verificacion['fecha']})")
    return 0


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
