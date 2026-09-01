"""Carga y validación del catálogo de fuentes.

Esquema: CONTRATO registro-de-fuente v1 (docs/f1-contratos.md).
"""

import json
from pathlib import Path


class ErrorCatalogo(Exception):
    """El catálogo no existe o viola el contrato."""


def cargar_catalogo(ruta):
    """Carga data/fuentes.json y valida la envoltura del contrato.

    Devuelve el diccionario {"version": int, "fuentes": list}.
    Lanza ErrorCatalogo ante archivo ausente, JSON inválido o
    envoltura que no cumpla el contrato. Nunca devuelve un catálogo
    parcialmente válido (fail-closed).
    """
    ruta = Path(ruta)
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ErrorCatalogo(f"catálogo inexistente: {ruta}") from exc
    except json.JSONDecodeError as exc:
        raise ErrorCatalogo(f"catálogo corrupto (JSON inválido): {ruta}: {exc}") from exc
    if not isinstance(datos, dict):
        raise ErrorCatalogo("catálogo: se esperaba un objeto JSON")
    version = datos.get("version")
    if not isinstance(version, int):
        raise ErrorCatalogo("catálogo: falta 'version' (entero)")
    fuentes = datos.get("fuentes")
    if not isinstance(fuentes, list):
        raise ErrorCatalogo("catálogo: falta 'fuentes' (lista)")
    return datos
