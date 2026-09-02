"""Servicio HTTP de lectura para agentes remotos (ADR-013, SPEC-9).

Contrato: docs/f1-contratos.md (CONTRATO servicio-infosalud v1).
API JSON de sólo lectura + capa MCP (JSON-RPC 2.0 en POST /mcp,
modo sin sesión). Sólo stdlib. El servicio nunca muta el catálogo
ni descarga del portal: la frescura pertenece a vigencia-verificar
y al sondeo (ADR-008). El token (opcional) llega por entorno
INFOSALUD_SERVICIO_TOKEN y jamás se registra en bitácoras.
"""

import io
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs

from infosalud import __version__
from infosalud.catalogo import ErrorCatalogo, cargar_catalogo
from infosalud.diccionario import (
    ErrorDiccionario,
    cargar as cargar_diccionario,
    ruta_diccionario,
)

PROTOCOL_VERSION_MCP = "2025-06-18"
FORMATOS_EXPORTACION = ("csv", "sqlite")
TIMEOUT_EXPORTAR = 300  # segundos; tope defensivo del subprocess


class ErrorServicio(Exception):
    """Fallo con código HTTP asociado (contrato servicio v1)."""

    def __init__(self, codigo, mensaje):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


def _cargar_catalogo(ruta):
    try:
        return cargar_catalogo(ruta)
    except ErrorCatalogo as exc:
        raise ErrorServicio(500, str(exc)) from exc


def _fuente(catalogo, id_fuente):
    for f in catalogo["fuentes"]:
        if f.get("id") == id_fuente:
            return f
    raise ErrorServicio(404, f"id inexistente: '{id_fuente}'")


def _ultima_verificacion(fuente):
    verificaciones = fuente.get("verificaciones") or []
    return verificaciones[-1] if verificaciones else None


def _coincide(fuente, q):
    if not q:
        return True
    q = q.lower()
    return any(q in str(fuente.get(campo, "")).lower()
               for campo in ("id", "titulo", "notas"))


def _lista(catalogo, seccion=None, formato=None, q=None):
    fuentes = [f for f in catalogo["fuentes"]
               if (not seccion or f.get("seccion") == seccion)
               and (not formato or f.get("formato") == formato)
               and _coincide(f, q)]
    return {"fuentes": fuentes, "total": len(fuentes)}


def _resumen(catalogo):
    por_seccion, por_vigencia = {}, {}
    for f in catalogo["fuentes"]:
        seccion = f.get("seccion", "?")
        por_seccion[seccion] = por_seccion.get(seccion, 0) + 1
        v = _ultima_verificacion(f)
        estado = v.get("resultado", "desconocida") if v else "desconocida"
        por_vigencia[estado] = por_vigencia.get(estado, 0) + 1
    cortes = [v["fecha"] for f in catalogo["fuentes"]
              for v in (f.get("verificaciones") or []) if v.get("fecha")]
    return {"fuentes": len(catalogo["fuentes"]),
            "por_seccion": por_seccion,
            "por_vigencia": por_vigencia,
            "corte": max(cortes) if cortes else None}


def _mapa(catalogo):
    return {
        "servicio": "infosalud-servicio",
        "contrato": "servicio-infosalud v1",
        "version": __version__,
        "adr": "ADR-013",
        "resumen": _resumen(catalogo),
        "endpoints": ["/", "/healthz", "/cobertura", "/fuentes",
                      "/fuentes/{id}",
                      "/fuentes/{id}/campos", "/fuentes/{id}/historia",
                      "/fuentes/{id}/archivo",
                      "/fuentes/{id}/archivo/meta",
                      "/fuentes/{id}/exportar?formato=csv|sqlite",
                      "POST /mcp (JSON-RPC 2.0)"],
    }


def _healthz(catalogo):
    resumen = _resumen(catalogo)
    return {"ok": True, "fuentes": resumen["fuentes"],
            "ultima_verificacion": resumen["corte"]}


def _diccionario(ruta_catalogo, id_fuente):
    catalogo = _cargar_catalogo(ruta_catalogo)
    _fuente(catalogo, id_fuente)  # 404 si el id no está en el catálogo
    ruta = ruta_diccionario(ruta_catalogo, id_fuente)
    try:
        diccionario = cargar_diccionario(ruta)
    except ErrorDiccionario as exc:
        raise ErrorServicio(500, f"diccionario corrupto: {exc}") from exc
    if diccionario is None:
        raise ErrorServicio(
            404, f"sin diccionario de datos para '{id_fuente}'")
    return diccionario


def _historia(catalogo, id_fuente):
    fuente = _fuente(catalogo, id_fuente)
    return {"id": id_fuente,
            "verificaciones": fuente.get("verificaciones") or []}


import re as _re

_ANIO = _re.compile(r"(?:19|20)\d{2}")


def _cobertura(catalogo):
    """Índice de cobertura: años detectados por fuente (título/URL/
    notas) y si el archivo ya está descargado y presente en disco."""
    filas = []
    for f in catalogo["fuentes"]:
        texto = " ".join([f.get("titulo", ""), f.get("url", ""),
                          f.get("notas", "")])
        anios = sorted({m.group(0) for m in _ANIO.finditer(texto)})
        vers = f.get("verificaciones") or []
        ultima = vers[-1] if vers else None
        ruta_local = (ultima or {}).get("ruta_local")
        descargado = bool(ruta_local and os.path.isfile(ruta_local))
        filas.append({
            "id": f.get("id"),
            "seccion": f.get("seccion"),
            "anios": anios,
            "vigencia": (ultima or {}).get("resultado", "desconocida"),
            "ultima_verificacion": (ultima or {}).get("fecha"),
            "descargado": descargado,
            "archivo": (os.path.basename(ruta_local)
                        if descargado else None),
        })
    return {"total": len(filas), "cobertura": filas}


CONTENT_TYPES = {
    ".xlsx": "application/vnd.openxmlformats-officedocument"
             ".spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".pdf": "application/pdf",
    ".html": "text/html; charset=utf-8",
    ".csv": "text/csv; charset=utf-8",
    ".zip": "application/zip",
}


def _verificacion_con_archivo(fuente):
    """Última verificación con huella y ruta local existente."""
    for v in reversed(fuente.get("verificaciones") or []):
        if v.get("huella") and v.get("ruta_local"):
            if os.path.isfile(v["ruta_local"]):
                return v
    return None


def _archivo_meta(ruta_catalogo, id_fuente):
    """Envelope del archivo verificado (contrato servicio v1):
    recomputa el sha256 en vivo; estado_integridad nunca se afirma
    sin verificación presente."""
    import hashlib
    catalogo = _cargar_catalogo(ruta_catalogo)
    fuente = _fuente(catalogo, id_fuente)
    verificacion = _verificacion_con_archivo(fuente)
    if verificacion is None:
        raise ErrorServicio(
            404, f"sin archivo local verificado para '{id_fuente}'")
    ruta = verificacion["ruta_local"]
    digest = hashlib.sha256()
    with open(ruta, "rb") as archivo:
        for bloque in iter(lambda: archivo.read(1 << 20), b""):
            digest.update(bloque)
    sha256 = digest.hexdigest()
    fecha = verificacion.get("fecha")
    return {
        "id": id_fuente,
        "titulo": fuente.get("titulo"),
        "nombre_archivo": os.path.basename(ruta),
        "formato": fuente.get("formato", "otro"),
        "tamanio_bytes": os.path.getsize(ruta),
        "sha256": sha256,
        "sha256_registrado": verificacion["huella"],
        "corte": fecha,
        "fecha_descarga": fecha,
        "url_origen_imss": fuente.get("url"),
        "origen": "IMSS",
        "estado_integridad": ("verificado"
                              if sha256 == verificacion["huella"]
                              else "alterado"),
        "estado_semantico": "sin_evaluar",
        "descarga_url": f"/fuentes/{id_fuente}/archivo",
    }


def _archivo_binario(ruta_catalogo, id_fuente):
    """Devuelve (bytes, nombre, content_type) del archivo verificado;
    exige integridad: si el sha256 vivo difiere del registrado,
    falla con 409 en lugar de servir contenido alterado."""
    import hashlib
    meta = _archivo_meta(ruta_catalogo, id_fuente)
    if meta["estado_integridad"] != "verificado":
        raise ErrorServicio(
            409, "integridad alterada: el sha256 del archivo local "
                 "no coincide con el registrado")
    catalogo = _cargar_catalogo(ruta_catalogo)
    fuente = _fuente(catalogo, id_fuente)
    ruta = _verificacion_con_archivo(fuente)["ruta_local"]
    with open(ruta, "rb") as archivo:
        datos = archivo.read()
    extension = os.path.splitext(ruta)[1].lower()
    return (datos, meta["nombre_archivo"],
            CONTENT_TYPES.get(extension, "application/octet-stream"))


def _exportar_zip(ruta_catalogo, id_fuente, formato):
    """Corre fuente-exportar a directorio temporal y devuelve el zip
    con los productos (ADR-011); el temporal se elimina al salir."""
    _fuente(_cargar_catalogo(ruta_catalogo), id_fuente)
    if formato not in FORMATOS_EXPORTACION:
        raise ErrorServicio(400, "formato inválido: use csv o sqlite")
    with tempfile.TemporaryDirectory(prefix="infosalud-export-") as tmp:
        r = subprocess.run(
            [sys.executable, "-m", "infosalud", "fuente-exportar",
             id_fuente, "--formato", formato, "--destino", tmp,
             "--catalogo", ruta_catalogo],
            capture_output=True, text=True, timeout=TIMEOUT_EXPORTAR)
        if r.returncode != 0:
            mensaje = (r.stderr or r.stdout
                       or "exportación fallida").strip()
            raise ErrorServicio(400, mensaje.splitlines()[-1])
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
            for base, _dirs, archivos in os.walk(tmp):
                for nombre in archivos:
                    ruta = os.path.join(base, nombre)
                    z.write(ruta, os.path.relpath(ruta, tmp))
        return buffer.getvalue(), f"{id_fuente}-{formato}.zip"


# ---------------------------------------------------------------- MCP

HERRAMIENTAS = [
    {"name": "mapa_servicio",
     "description": "Mapa del servicio: versión, corte, resumen de "
                    "fuentes por sección y vigencia, endpoints.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "buscar_fuentes",
     "description": "Lista fuentes del catálogo con su vigencia; "
                    "filtros opcionales por texto (id/título/notas), "
                    "sección y formato.",
     "inputSchema": {"type": "object", "properties": {
         "q": {"type": "string"},
         "seccion": {"type": "string"},
         "formato": {"type": "string"}}}},
    {"name": "detalle_fuente",
     "description": "Registro completo de una fuente: url, formato, "
                    "periodicidad, notas y verificaciones (huella "
                    "sha256, fecha, resultado, url_previa, estructura).",
     "inputSchema": {"type": "object", "properties": {
         "id": {"type": "string"}}, "required": ["id"]}},
    {"name": "diccionario_fuente",
     "description": "Diccionario de datos (diccionario-de-fuente v1) "
                    "de una fuente, si existe.",
     "inputSchema": {"type": "object", "properties": {
         "id": {"type": "string"}}, "required": ["id"]}},
    {"name": "historia_fuente",
     "description": "Historial append-only de verificaciones de "
                    "vigencia de una fuente.",
     "inputSchema": {"type": "object", "properties": {
         "id": {"type": "string"}}, "required": ["id"]}},
    {"name": "cobertura_fuentes",
     "description": "Índice de cobertura: para cada fuente, años "
                    "detectados (título/URL/notas), vigencia, fecha "
                    "de última verificación y si el archivo ya está "
                    "descargado en el servidor.",
     "inputSchema": {"type": "object", "properties": {
         "seccion": {"type": "string"}}}},
    {"name": "archivo_fuente",
     "description": "Metadatos del archivo original verificado "
                    "(nombre, tamaño, sha256 recomputado en vivo, "
                    "corte, URL de origen IMSS, estado de "
                    "integridad); el binario se descarga en "
                    "GET /fuentes/{id}/archivo.",
     "inputSchema": {"type": "object", "properties": {
         "id": {"type": "string"}}, "required": ["id"]}},
    {"name": "exportar_fuente",
     "description": "Exporta el archivo verificado a CSV o SQLite con "
                    "evidencia (ADR-011) en el directorio de "
                    "exportaciones del servidor; devuelve las rutas "
                    "de los productos.",
     "inputSchema": {"type": "object", "properties": {
         "id": {"type": "string"},
         "formato": {"type": "string",
                     "enum": list(FORMATOS_EXPORTACION)}},
         "required": ["id"]}},
]


def _obligatorio(argumentos, campo):
    valor = argumentos.get(campo)
    if not isinstance(valor, str) or not valor:
        raise ErrorServicio(400, f"parámetro requerido: '{campo}'")
    return valor


def _exportar_resumen(catalogo, id_fuente, formato):
    """Exporta al destino por defecto del CLI y devuelve el resumen
    JSON (los productos quedan en data/exportaciones del servidor)."""
    _fuente(catalogo, id_fuente)
    if formato not in FORMATOS_EXPORTACION:
        raise ErrorServicio(400, "formato inválido: use csv o sqlite")
    r = subprocess.run(
        [sys.executable, "-m", "infosalud", "fuente-exportar",
         id_fuente, "--formato", formato, "--catalogo", catalogo,
         "--json"],
        capture_output=True, text=True, timeout=TIMEOUT_EXPORTAR)
    if r.returncode != 0:
        mensaje = (r.stderr or r.stdout or "exportación fallida").strip()
        raise ErrorServicio(400, mensaje.splitlines()[-1])
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError as exc:
        raise ErrorServicio(500, "salida no-JSON de fuente-exportar") \
            from exc


def _llamada_tool(ruta_catalogo, nombre, argumentos):
    """Ejecuta una tool y devuelve su resultado (dict) o lanza
    ErrorServicio; el error viaja como isError (espec MCP: los
    fallos de la herramienta no son errores de protocolo)."""
    catalogo = _cargar_catalogo(ruta_catalogo)
    if nombre == "mapa_servicio":
        return _mapa(catalogo)
    if nombre == "buscar_fuentes":
        return _lista(catalogo, argumentos.get("seccion"),
                      argumentos.get("formato"), argumentos.get("q"))
    if nombre == "detalle_fuente":
        return _fuente(catalogo, _obligatorio(argumentos, "id"))
    if nombre == "diccionario_fuente":
        return _diccionario(ruta_catalogo,
                            _obligatorio(argumentos, "id"))
    if nombre == "historia_fuente":
        return _historia(catalogo, _obligatorio(argumentos, "id"))
    if nombre == "archivo_fuente":
        return _archivo_meta(ruta_catalogo,
                             _obligatorio(argumentos, "id"))
    if nombre == "cobertura_fuentes":
        catalogo = _cargar_catalogo(ruta_catalogo)
        cobertura = _cobertura(catalogo)
        seccion = argumentos.get("seccion")
        if seccion:
            cobertura["cobertura"] = [
                fila for fila in cobertura["cobertura"]
                if fila["seccion"] == seccion]
            cobertura["total"] = len(cobertura["cobertura"])
        return cobertura
    if nombre == "exportar_fuente":
        return _exportar_resumen(
            ruta_catalogo, _obligatorio(argumentos, "id"),
            argumentos.get("formato", "csv"))
    raise ErrorServicio(404, f"herramienta desconocida: '{nombre}'")


def _rpc_error(id_peticion, codigo_error, mensaje):
    return {"jsonrpc": "2.0", "id": id_peticion,
            "error": {"code": codigo_error, "message": mensaje}}


def _mcp_responder(ruta_catalogo, cuerpo):
    """Procesa una petición JSON-RPC 2.0; devuelve (codigo_http,
    objeto|None). None con 202 para notificaciones."""
    try:
        peticion = json.loads(cuerpo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return 400, _rpc_error(None, -32700, "JSON inválido")
    if not isinstance(peticion, dict):
        return 400, _rpc_error(None, -32600,
                               "la petición debe ser un objeto JSON-RPC")
    metodo = peticion.get("method", "")
    if not isinstance(metodo, str):
        return 400, _rpc_error(peticion.get("id"), -32600,
                               "'method' debe ser texto")
    if metodo.startswith("notifications/"):
        return 202, None
    id_peticion = peticion.get("id")
    try:
        respuesta = _mcp_despachar(ruta_catalogo, peticion, metodo,
                                   id_peticion)
    except ErrorServicio as exc:
        return 200, _rpc_error(id_peticion, -32603, exc.mensaje)
    except Exception as exc:  # última red: la conexión nunca muere
        return 200, _rpc_error(id_peticion, -32603,
                               f"error interno: {type(exc).__name__}")
    return respuesta


def _mcp_despachar(ruta_catalogo, peticion, metodo, id_peticion):
    if metodo == "initialize":
        return 200, {"jsonrpc": "2.0", "id": id_peticion, "result": {
            "protocolVersion": PROTOCOL_VERSION_MCP,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "infosalud-servicio",
                           "version": __version__}}}
    if metodo == "tools/list":
        return 200, {"jsonrpc": "2.0", "id": id_peticion,
                     "result": {"tools": HERRAMIENTAS}}
    if metodo == "tools/call":
        parametros = peticion.get("params") or {}
        if not isinstance(parametros, dict):
            return 400, _rpc_error(id_peticion, -32602,
                                   "'params' debe ser un objeto")
        nombre = parametros.get("name")
        argumentos = parametros.get("arguments") or {}
        if not isinstance(argumentos, dict):
            return 400, _rpc_error(id_peticion, -32602,
                                   "'arguments' debe ser un objeto")
        try:
            if not isinstance(nombre, str) or not nombre:
                raise ErrorServicio(400, "falta 'name' de la tool")
            resultado = _llamada_tool(ruta_catalogo, nombre,
                                      argumentos)
        except ErrorServicio as exc:
            return 200, {"jsonrpc": "2.0", "id": id_peticion,
                         "result": {
                             "content": [{"type": "text",
                                          "text": exc.mensaje}],
                             "isError": True}}
        return 200, {"jsonrpc": "2.0", "id": id_peticion, "result": {
            "content": [{"type": "text",
                         "text": json.dumps(resultado,
                                            ensure_ascii=False)}],
            "isError": False}}
    return 200, _rpc_error(id_peticion, -32601,
                           f"método desconocido: '{metodo}'")


# ------------------------------------------------------------- HTTP

class Manejador(BaseHTTPRequestHandler):
    server_version = "infosalud-servicio/" + __version__

    def _autorizado(self):
        token = getattr(self.server, "token", None)
        if not token:
            return True
        return self.headers.get("Authorization", "") == f"Bearer {token}"

    def _enviar_json(self, codigo, objeto):
        cuerpo = json.dumps(objeto, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type",
                         "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):  # noqa: N802 (API de http.server)
        if not self._autorizado():
            return self._enviar_json(401, {"error": "no autorizado"})
        partes = urlsplit(self.path)
        ruta = partes.path.rstrip("/") or "/"
        query = {k: v[0] for k, v in parse_qs(partes.query).items()}
        try:
            catalogo = _cargar_catalogo(self.server.catalogo)
            if ruta == "/":
                return self._enviar_json(200, _mapa(catalogo))
            if ruta == "/healthz":
                return self._enviar_json(200, _healthz(catalogo))
            if ruta == "/cobertura":
                return self._enviar_json(
                    200, _cobertura(catalogo))
            piezas = [p for p in ruta.split("/") if p]
            if piezas and piezas[0] == "fuentes":
                if len(piezas) == 1:
                    return self._enviar_json(200, _lista(
                        catalogo, query.get("seccion"),
                        query.get("formato"), query.get("q")))
                if len(piezas) == 2:
                    return self._enviar_json(
                        200, _fuente(catalogo, piezas[1]))
                if len(piezas) == 3 and piezas[2] == "campos":
                    return self._enviar_json(
                        200, _diccionario(self.server.catalogo,
                                          piezas[1]))
                if len(piezas) == 3 and piezas[2] == "historia":
                    return self._enviar_json(
                        200, _historia(catalogo, piezas[1]))
                if len(piezas) == 3 and piezas[2] == "archivo":
                    datos, nombre, tipo = _archivo_binario(
                        self.server.catalogo, piezas[1])
                    self.send_response(200)
                    self.send_header("Content-Type", tipo)
                    self.send_header("Content-Disposition",
                                     f'attachment; filename="{nombre}"')
                    self.send_header("Content-Length", str(len(datos)))
                    self.end_headers()
                    return self.wfile.write(datos)
                if (len(piezas) == 4 and piezas[2] == "archivo"
                        and piezas[3] == "meta"):
                    return self._enviar_json(
                        200, _archivo_meta(self.server.catalogo,
                                           piezas[1]))
                if len(piezas) == 3 and piezas[2] == "exportar":
                    cuerpo, nombre = _exportar_zip(
                        self.server.catalogo, piezas[1],
                        query.get("formato", "csv"))
                    self.send_response(200)
                    self.send_header("Content-Type", "application/zip")
                    self.send_header("Content-Disposition",
                                     f'attachment; filename="{nombre}"')
                    self.send_header("Content-Length",
                                     str(len(cuerpo)))
                    self.end_headers()
                    return self.wfile.write(cuerpo)
            raise ErrorServicio(404, f"ruta desconocida: {ruta}")
        except ErrorServicio as exc:
            return self._enviar_json(exc.codigo, {"error": exc.mensaje})

    def do_POST(self):  # noqa: N802 (API de http.server)
        if not self._autorizado():
            return self._enviar_json(401, {"error": "no autorizado"})
        partes = urlsplit(self.path)
        if partes.path.rstrip("/") != "/mcp":
            return self._enviar_json(
                404, {"error": f"ruta desconocida: {partes.path}"})
        longitud = int(self.headers.get("Content-Length") or 0)
        if longitud > 1_048_576:  # 1 MiB; JSON-RPC no necesita más
            return self._enviar_json(
                413, {"error": "cuerpo demasiado grande"})
        cuerpo = self.rfile.read(longitud) if longitud else b""
        try:
            codigo, respuesta = _mcp_responder(
                self.server.catalogo, cuerpo)
        except ErrorServicio as exc:
            return self._enviar_json(exc.codigo,
                                     {"error": exc.mensaje})
        if respuesta is None:
            self.send_response(202)
            self.end_headers()
            return
        return self._enviar_json(codigo, respuesta)

    def log_message(self, formato, *argumentos):  # bitácora mínima
        sys.stderr.write("%s - %s\n"
                         % (self.address_string(), formato % argumentos))


def crear_servidor(catalogo, host="127.0.0.1", puerto=8081, token=None):
    """Crea el servidor (ThreadingHTTPServer) sin atender peticiones;
    usado por servir() y por los tests con puerto efímero."""
    servidor = ThreadingHTTPServer((host, puerto), Manejador)
    servidor.catalogo = catalogo
    servidor.token = token
    return servidor


def servir(args):
    """Subcomando `servir`: bloquea sirviendo HTTP hasta interrumpir."""
    token = os.environ.get("INFOSALUD_SERVICIO_TOKEN") or None
    servidor = crear_servidor(args.catalogo, args.host, args.puerto,
                              token)
    print(f"infosalud-servicio {__version__} en "
          f"http://{args.host}:{args.puerto} "
          f"(catálogo: {args.catalogo}; "
          f"token: {'sí' if token else 'no'})")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
    return 0
