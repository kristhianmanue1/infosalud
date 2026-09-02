"""SPEC-9 (ADR-013): servicio HTTP de lectura para agentes.

Casos DADO/CUANDO/ENTONCES de docs/f1-specs.md SPEC-9 sobre el
contrato servicio-infosalud v1 (docs/f1-contratos.md). El servidor
se levanta en un puerto efímero (127.0.0.1:0) contra un catálogo
temporal; nunca toca data/ del repositorio ni la red externa.
"""

import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from infosalud.servicio import crear_servidor

ID = "fuente-prueba"
FUENTE = {
    "id": ID, "seccion": "catalogos", "titulo": "Fuente de prueba",
    "url": "http://infosalud.imss.gob.mx:8080/ARCHIVOS/x.xlsx",
    "formato": "xlsx",
    "verificaciones": [
        {"fecha": "2026-09-02", "resultado": "vigente",
         "huella": "a" * 64, "ruta_local": "data/descargas/x/x.xlsx"},
    ],
}


class PruebaServicio(unittest.TestCase):
    token = None

    def setUp(self):
        self.dir_tmp = tempfile.TemporaryDirectory()
        base = self.dir_tmp.name
        os.makedirs(os.path.join(base, "diccionarios"))
        self.catalogo = os.path.join(base, "fuentes.json")
        with open(self.catalogo, "w", encoding="utf-8") as archivo:
            json.dump({"version": 1, "fuentes": [FUENTE]}, archivo,
                      ensure_ascii=False)
        with open(os.path.join(base, "diccionarios", ID + ".json"),
                  "w", encoding="utf-8") as archivo:
            json.dump({"id": ID, "campos": [
                {"nombre": "CLAVE", "tipo": "clave"}]}, archivo)
        self.servidor = crear_servidor(self.catalogo, "127.0.0.1", 0,
                                       self.token)
        self.hilo = threading.Thread(
            target=self.servidor.serve_forever, daemon=True)
        self.hilo.start()
        self.base = "http://127.0.0.1:" \
            f"{self.servidor.server_address[1]}"

    def tearDown(self):
        self.servidor.shutdown()
        self.servidor.server_close()
        self.hilo.join(timeout=5)
        self.dir_tmp.cleanup()

    def _peticion(self, ruta, cuerpo=None, metodo=None, token=None,
                  datos_crudos=None):
        encabezados = {}
        if token is None and self.token:
            token = self.token  # autenticación por defecto del caso
        if token:
            encabezados["Authorization"] = f"Bearer {token}"
        datos = datos_crudos
        if cuerpo is not None:
            datos = json.dumps(cuerpo).encode("utf-8")
            encabezados["Content-Type"] = "application/json"
        peticion = urllib.request.Request(
            self.base + ruta, data=datos, headers=encabezados,
            method=metodo or ("POST" if datos is not None else "GET"))
        try:
            with urllib.request.urlopen(peticion, timeout=10) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()

    def _json(self, ruta, **kw):
        codigo, cuerpo = self._peticion(ruta, **kw)
        return codigo, json.loads(cuerpo.decode("utf-8"))

    def test_mapa_y_healthz(self):
        """DADO el servicio en pie CUANDO GET / y /healthz ENTONCES
        200 con contrato, versión, resumen y ok."""
        codigo, mapa = self._json("/")
        self.assertEqual(codigo, 200)
        self.assertEqual(mapa["contrato"], "servicio-infosalud v1")
        self.assertEqual(mapa["resumen"]["fuentes"], 1)
        codigo, salud = self._json("/healthz")
        self.assertEqual(codigo, 200)
        self.assertTrue(salud["ok"])
        self.assertEqual(salud["fuentes"], 1)

    def test_lista_con_filtros(self):
        """DADO filtros por sección/texto CUANDO GET /fuentes
        ENTONCES 200 con {fuentes, total} respetando el filtro."""
        codigo, cuerpo = self._json("/fuentes?seccion=catalogos")
        self.assertEqual(codigo, 200)
        self.assertEqual(cuerpo["total"], 1)
        codigo, cuerpo = self._json("/fuentes?seccion=hospital")
        self.assertEqual(codigo, 200)
        self.assertEqual(cuerpo["total"], 0)
        codigo, cuerpo = self._json("/fuentes?q=prueba")
        self.assertEqual(cuerpo["total"], 1)

    def test_detalle_e_inexistente(self):
        """DADO un id existente CUANDO GET /fuentes/{id} ENTONCES 200
        con verificaciones; DADO id inexistente ENTONCES 404 JSON."""
        codigo, cuerpo = self._json(f"/fuentes/{ID}")
        self.assertEqual(codigo, 200)
        self.assertEqual(cuerpo["verificaciones"][0]["huella"], "a" * 64)
        codigo, cuerpo = self._json("/fuentes/id-fantasma")
        self.assertEqual(codigo, 404)
        self.assertIn("error", cuerpo)

    def test_campos_e_historia(self):
        """DADO diccionario presente CUANDO GET campos ENTONCES 200;
        DADO historia CUANDO GET ENTONCES verificaciones append-only."""
        codigo, cuerpo = self._json(f"/fuentes/{ID}/campos")
        self.assertEqual(codigo, 200)
        self.assertEqual(cuerpo["campos"][0]["nombre"], "CLAVE")
        codigo, cuerpo = self._json(f"/fuentes/{ID}/historia")
        self.assertEqual(codigo, 200)
        self.assertEqual(len(cuerpo["verificaciones"]), 1)

    def test_ruta_desconocida(self):
        """DADO una ruta inexistente ENTONCES 404 JSON."""
        codigo, cuerpo = self._json("/otra-cosa")
        self.assertEqual(codigo, 404)
        self.assertIn("error", cuerpo)

    def test_exportar_sin_archivo_da_400(self):
        """DADO fuente cuya verificación apunta a ruta inexistente
        CUANDO GET exportar ENTONCES 400 con causa (nunca 500)."""
        codigo, cuerpo = self._json(
            f"/fuentes/{ID}/exportar?formato=csv")
        self.assertEqual(codigo, 400)
        self.assertIn("error", cuerpo)

    def test_archivo_meta_y_binario(self):
        """DADO un archivo local existente con huella registrada
        CUANDO GET archivo/meta y archivo ENTONCES envelope con
        sha256 recomputado igual al registrado (verificado) y el
        binario coincide byte a byte."""
        import hashlib
        contenido = b"contenido-de-prueba" * 100
        ruta_local = os.path.join(self.dir_tmp.name, "archivo.xlsx")
        with open(ruta_local, "wb") as archivo:
            archivo.write(contenido)
        huella = hashlib.sha256(contenido).hexdigest()
        with open(self.catalogo, encoding="utf-8") as archivo:
            datos = json.load(archivo)
        datos["fuentes"][0]["verificaciones"][0]["ruta_local"] = \
            ruta_local
        datos["fuentes"][0]["verificaciones"][0]["huella"] = huella
        with open(self.catalogo, "w", encoding="utf-8") as archivo:
            json.dump(datos, archivo, ensure_ascii=False)
        codigo, meta = self._json(f"/fuentes/{ID}/archivo/meta")
        self.assertEqual(codigo, 200)
        self.assertEqual(meta["estado_integridad"], "verificado")
        self.assertEqual(meta["sha256"], huella)
        self.assertEqual(meta["tamanio_bytes"], len(contenido))
        self.assertEqual(meta["origen"], "IMSS")
        self.assertEqual(meta["estado_semantico"], "sin_evaluar")
        codigo, binario = self._peticion(f"/fuentes/{ID}/archivo")
        self.assertEqual(codigo, 200)
        self.assertEqual(binario, contenido)

    def test_archivo_meta_sin_archivo_da_404(self):
        """DADO ruta_local inexistente CUANDO GET archivo/meta
        ENTONCES 404 (nunca se afirma integridad sin archivo)."""
        codigo, cuerpo = self._json(f"/fuentes/{ID}/archivo/meta")
        self.assertEqual(codigo, 404)
        self.assertIn("error", cuerpo)

    def test_mcp_ciclo_completo(self):
        """DADO MCP CUANDO initialize → tools/list → tools/call
        ENTONCES protocolo y herramientas correctas; id inexistente
        produce isError (no error de protocolo)."""
        codigo, r = self._json("/mcp", cuerpo={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {}})
        self.assertEqual(codigo, 200)
        self.assertEqual(r["result"]["protocolVersion"], "2025-06-18")
        codigo, r = self._json("/mcp", cuerpo={
            "jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        self.assertEqual(codigo, 200)
        nombres = {t["name"] for t in r["result"]["tools"]}
        self.assertEqual(len(nombres), 7)
        self.assertIn("detalle_fuente", nombres)
        self.assertIn("archivo_fuente", nombres)
        codigo, r = self._json("/mcp", cuerpo={
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "detalle_fuente",
                       "arguments": {"id": ID}}})
        self.assertEqual(codigo, 200)
        self.assertFalse(r["result"]["isError"])
        registro = json.loads(r["result"]["content"][0]["text"])
        self.assertEqual(registro["id"], ID)
        codigo, r = self._json("/mcp", cuerpo={
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "detalle_fuente",
                       "arguments": {"id": "id-fantasma"}}})
        self.assertTrue(r["result"]["isError"])

    def test_mcp_errores_y_notificaciones(self):
        """DADO método desconocido ENTONCES -32601; DADO notificación
        ENTONCES 202 sin cuerpo; DADO JSON inválido ENTONCES -32700."""
        codigo, r = self._json("/mcp", cuerpo={
            "jsonrpc": "2.0", "id": 5, "method": "resources/list"})
        self.assertEqual(r["error"]["code"], -32601)
        codigo, cuerpo = self._peticion("/mcp", cuerpo={
            "jsonrpc": "2.0", "method": "notifications/initialized"})
        self.assertEqual(codigo, 202)
        self.assertEqual(cuerpo, b"")
        codigo, cuerpo = self._peticion(
            "/mcp", metodo="POST", datos_crudos=b"no-es-json")
        self.assertEqual(codigo, 400)
        self.assertEqual(json.loads(cuerpo)["error"]["code"], -32700)


class PruebaServicioConToken(PruebaServicio):
    """DADO token configurado CUANDO petición sin Authorization
    ENTONCES 401; con token correcto ENTONCES 200."""

    token = "secreto-de-entorno"

    def test_token_requerido(self):
        codigo, cuerpo = self._json("/fuentes", token="")
        self.assertEqual(codigo, 401)
        self.assertIn("error", cuerpo)
        codigo, _cuerpo = self._peticion("/fuentes")
        self.assertEqual(codigo, 200)


if __name__ == "__main__":
    unittest.main()