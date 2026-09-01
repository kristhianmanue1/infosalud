"""Vigencia de una fuente: huella y máquina de estados.

Estados (docs/f1-contratos.md): desconocida → vigente | cambiada |
inaccesible. Un fallo de lectura nunca produce éxito inferido.
"""

import hashlib
from datetime import date

BUFER = 65536


def calcular_huella(ruta):
    """Devuelve la huella sha256 (hex) del archivo en ruta.

    Propaga OSError (archivo inexistente o ilegible): el llamador
    debe registrar 'inaccesible', nunca inferir éxito.
    """
    huella = hashlib.sha256()
    with open(ruta, "rb") as archivo:
        for bloque in iter(lambda: archivo.read(BUFER), b""):
            huella.update(bloque)
    return huella.hexdigest()


def determinar_resultado(huella, verificaciones):
    """Determina el estado según la huella nueva y el historial.

    - Sin huella previa (estado desconocida): vigente.
    - Igual a la última huella: vigente; distinta: cambiada.
    """
    previas = [v["huella"] for v in verificaciones if v.get("huella")]
    if not previas:
        return "vigente"
    return "vigente" if huella == previas[-1] else "cambiada"


def fecha_hoy():
    """Fecha ISO-8601 de la verificación (trazabilidad, REQ-8)."""
    return date.today().isoformat()
