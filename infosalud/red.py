"""Descarga de sólo lectura de una fuente (ADR-008, SPEC-4).

Único comando con red: GET al host de la URL registrada en el
catálogo (la restricción de host *.imss.gob.mx se aplica en el alta,
CONTRATO registro-de-fuente v1). Aquí se refuerzan las salvaguardas
declaradas en ADR-008: timeout explícito, tamaño máximo, verificación
mínima de contenido, sin redirects fuera del host original y
escritura atómica (temporal + rename). Fail-closed: cualquier fallo
levanta ErrorRed con causa declarada; nunca éxito inferido.
"""

import os
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 30                  # segundos; la red lenta no cuelga al agente
TAM_MAX = 200 * 1024 * 1024   # 200 MiB, muy por encima del portal
BUFER = 65536


class ErrorRed(Exception):
    """Fallo de descarga: la causa se registra, nunca se infiere éxito."""


class _RedirectsProhibidos(urllib.request.HTTPRedirectHandler):
    """Redirect handler que rechaza saltos a otro host (SSRF-lite)."""

    def __init__(self, host_original):
        self.host_original = host_original

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        nuevo = urllib.parse.urlsplit(newurl).hostname or ""
        if nuevo != self.host_original:
            raise ErrorRed(
                f"redirect a host no autorizado: {nuevo or newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def descargar(url, destino, formato, timeout=None, tam_max=None):
    """Descarga url a destino (GET) y devuelve la ruta final.

    Escritura atómica: temporal + rename, de modo que la huella
    posterior nunca se calcula sobre un archivo a medias. Lanza
    ErrorRed ante cualquier fallo declarado en el contrato.
    """
    timeout = TIMEOUT if timeout is None else timeout
    tam_max = TAM_MAX if tam_max is None else tam_max
    esquema = urllib.parse.urlsplit(url).scheme
    if esquema not in ("http", "https"):
        raise ErrorRed(f"esquema no permitido: {esquema or url!r}")
    host = urllib.parse.urlsplit(url).hostname or ""
    abridor = urllib.request.build_opener(_RedirectsProhibidos(host))
    peticion = urllib.request.Request(url, method="GET")
    try:
        with abridor.open(peticion, timeout=timeout) as respuesta:
            _verificar_estado(respuesta.getcode())
            _leer_atomico(respuesta, destino, formato, tam_max)
    except ErrorRed:
        raise
    except urllib.error.HTTPError as exc:
        raise ErrorRed(f"HTTP {exc.code}: {exc.reason}") from exc
    except OSError as exc:
        raise ErrorRed(f"red indisponible: {exc}") from exc
    return destino


def nombre_desde_url(url):
    """Nombre de archivo sugerido por la ruta de la URL."""
    ruta = urllib.parse.urlsplit(url).path
    nombre = urllib.parse.unquote(ruta.rsplit("/", 1)[-1]) if ruta else ""
    return nombre or "descarga"


def _verificar_estado(codigo):
    if codigo != 200:
        raise ErrorRed(f"estado HTTP inesperado: {codigo}")


def _leer_atomico(respuesta, destino, formato, tam_max):
    """Lee la respuesta con tope de tamaño y la deja en destino."""
    temporal = destino + ".tmp"
    os.makedirs(os.path.dirname(os.path.abspath(destino)), exist_ok=True)
    recibido = 0
    cabecera = b""
    try:
        with open(temporal, "wb") as archivo:
            while True:
                bloque = respuesta.read(BUFER)
                if not bloque:
                    break
                if not cabecera:
                    cabecera = bloque[:8]
                recibido += len(bloque)
                if recibido > tam_max:
                    raise ErrorRed(
                        f"respuesta excede el tamaño máximo ({tam_max})")
                archivo.write(bloque)
            _verificar_contenido(formato, cabecera, recibido)
        os.replace(temporal, destino)
    except ErrorRed:
        _descartar(temporal)
        raise
    except OSError as exc:
        _descartar(temporal)
        raise ErrorRed(f"escritura local fallida: {exc}") from exc


def _descartar(temporal):
    try:
        os.remove(temporal)
    except OSError:
        pass


def _verificar_contenido(formato, cabecera, recibido):
    """Verificación mínima: rechaza p. ej. un HTML 200 con nombre xlsx."""
    if recibido == 0:
        raise ErrorRed("respuesta vacía")
    if formato == "xlsx" and not cabecera.startswith(b"PK"):
        raise ErrorRed("contenido sin firma zip para formato xlsx")
    if formato == "pdf" and not cabecera.startswith(b"%PDF"):
        raise ErrorRed("contenido sin firma PDF")
    if formato != "html" and cabecera.lstrip()[:1] == b"<":
        raise ErrorRed(f"contenido parece HTML para formato {formato}")
