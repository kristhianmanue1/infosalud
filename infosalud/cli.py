"""CLI de Infosalud Nexus.

Contrato: docs/f1-contratos.md (CONTRATO cli-infosalud v1.1).
Cascarón F2: implementa --version y fuente-lista. Los demás
comandos del contrato se agregan en F3; no se registran aquí
para no anunciar interfaces inexistentes.
"""

import argparse
import json
import sys

from infosalud import __version__
from infosalud.catalogo import ErrorCatalogo, cargar_catalogo

CATALOGO_POR_DEFECTO = "data/fuentes.json"


def _construir_parser():
    parser = argparse.ArgumentParser(
        prog="infosalud",
        description="Catálogo local de fuentes de Infosalud (sin red).",
    )
    parser.add_argument("--version", action="version",
                        version=f"infosalud {__version__}")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_lista = sub.add_parser(
        "fuente-lista",
        help="lista las fuentes del catálogo",
    )
    p_lista.add_argument("--catalogo", default=CATALOGO_POR_DEFECTO,
                         help="ruta del catálogo JSON")
    p_lista.add_argument("--seccion", help="filtra por sección")
    p_lista.add_argument("--formato", help="filtra por formato")
    p_lista.add_argument("--json", action="store_true",
                         help="salida JSON parseable (ADR-006)")
    return parser


def main(argv=None):
    args = _construir_parser().parse_args(argv)
    if args.comando == "fuente-lista":
        return _fuente_lista(args)
    return 2


def _fuente_lista(args):
    try:
        catalogo = cargar_catalogo(args.catalogo)
    except ErrorCatalogo as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    fuentes = catalogo["fuentes"]
    if args.seccion:
        fuentes = [f for f in fuentes if f.get("seccion") == args.seccion]
    if args.formato:
        fuentes = [f for f in fuentes if f.get("formato") == args.formato]
    if args.json:
        print(json.dumps({"fuentes": fuentes}, ensure_ascii=False))
    else:
        for fuente in fuentes:
            print(f"{fuente['id']}\t{fuente['titulo']}")
        print(f"{len(fuentes)} fuente(s)")
    return 0
