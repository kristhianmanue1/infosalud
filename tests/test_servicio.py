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

    def test_cobertura(self):
        """DADO el catálogo de prueba CUANDO GET /cobertura ENTONCES
        cada fuente reporta años detectados y estado de descarga."""
        codigo, cuerpo = self._json("/cobertura")
        self.assertEqual(codigo, 200)
        self.assertEqual(cuerpo["total"], 1)
        fila = cuerpo["cobertura"][0]
        self.assertEqual(fila["id"], ID)
        self.assertIn("anios", fila)
        self.assertFalse(fila["descargado"])  # ruta_local no existe

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

    def test_archivo_fuera_de_perimetro_da_403(self):
        """Ronda adversarial 2026-09-02: DADO catálogo manipulado con
        ruta_local fuera del directorio del catálogo (huella
        correcta) CUANDO GET archivo/meta y archivo ENTONCES 403 y
        el contenido jamás se sirve."""
        import hashlib
        base = tempfile.mkdtemp(dir=self.dir_tmp.name)
        os.makedirs(os.path.join(base, "data", "diccionarios"))
        secreto = os.path.join(base, "SECRETO-FUERA.txt")
        contenido = b"confidencial"
        with open(secreto, "wb") as archivo:
            archivo.write(contenido)
        huella = hashlib.sha256(contenido).hexdigest()
        fuente = dict(FUENTE, verificaciones=[{
            "fecha": "2026-09-02", "resultado": "vigente",
            "huella": huella, "ruta_local": secreto}])
        catalogo = os.path.join(base, "data", "fuentes.json")
        with open(catalogo, "w", encoding="utf-8") as archivo:
            json.dump({"version": 1, "fuentes": [fuente]}, archivo)
        servidor = crear_servidor(catalogo, "127.0.0.1", 0)
        hilo = threading.Thread(target=servidor.serve_forever,
                                daemon=True)
        hilo.start()
        base_url_anterior = self.base
        self.servidor, self.base = servidor, \
            f"http://127.0.0.1:{servidor.server_address[1]}"
        try:
            for ruta in (f"/fuentes/{ID}/archivo/meta",
                         f"/fuentes/{ID}/archivo"):
                codigo, cuerpo = self._peticion(ruta)
                self.assertEqual(codigo, 403, ruta)
                self.assertIn(b"per", cuerpo)
        finally:
            self.base = base_url_anterior
            servidor.shutdown()
            servidor.server_close()
            hilo.join(timeout=5)

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
        self.assertEqual(len(nombres), 10)
        self.assertIn("detalle_fuente", nombres)
        self.assertIn("archivo_fuente", nombres)
        self.assertIn("cobertura_fuentes", nombres)
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

    def test_mcp_entradas_hostiles_no_tumban_la_conexion(self):
        """Ronda adversarial 2026-09-02: DADO params/arguments no-dict,
        cuerpo array, cuerpo texto o cuerpo numérico ENTONCES siempre
        hay respuesta JSON-RPC (sin conexión cortada) con código
        -32600/-32602 o resultado isError."""
        hostiles = [
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
             "params": ["x"]},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
             "params": {"name": "detalle_fuente", "arguments": [1]}},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call"},
            [1, 2, 3],
            "\"hola\"",
            42,
        ]
        for i, cuerpo in enumerate(hostiles):
            codigo, r = self._json("/mcp", cuerpo=cuerpo)
            self.assertIn(codigo, (200, 400), f"caso {i}")
            fallo = ("error" in r
                     or r.get("result", {}).get("isError") is True)
            self.assertTrue(fallo, f"caso {i}: {r}")


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


# ---------------------------------------------------------- SPEC-12

def _xlsx_datos(filas, nombre_hoja="Catalogo"):
    """xlsx mínimo de una hoja con filas inlineStr numeradas."""
    import io
    import zipfile
    buffer = io.BytesIO()
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"

    def fila(celdas, numero):
        cuerpo = "".join(
            f'<c r="{chr(65 + i)}{numero}" t="inlineStr">'
            f"<is><t>{v}</t></is></c>"
            for i, v in enumerate(celdas))
        return f'<row r="{numero}">{cuerpo}</row>'

    cuerpo_hoja = "".join(
        fila(celdas, numero)
        for numero, celdas in enumerate(filas, start=1))
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("xl/workbook.xml",
                   f'<?xml version="1.0"?><workbook xmlns="{ns}" '
                   'xmlns:r="http://schemas.openxmlformats.org/'
                   'officeDocument/2006/relationships"><sheets>'
                   f'<sheet name="{nombre_hoja}" sheetId="1" '
                   'r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0"?>'
                   '<Relationships xmlns="http://schemas.'
                   'openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Target='
                   '"worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml",
                   f'<?xml version="1.0"?><worksheet xmlns="{ns}">'
                   f"<sheetData>{cuerpo_hoja}</sheetData>"
                   "</worksheet>")
    return buffer.getvalue()


class PruebaDatosFuente(unittest.TestCase):
    """SPEC-12 (ADR-014 fase 2): GET/HEAD /fuentes/{id}/datos,
    ETag compuesto, 304, segmentación por perfil y tool MCP
    datos_fuente."""

    def setUp(self):
        self.dir_tmp = tempfile.TemporaryDirectory()
        base = self.dir_tmp.name
        # xlsx: fila 1 total, fila 2 encabezados, filas 3-5 datos.
        self.filas = [["TOTAL", ""],
                      ["CLAVE", "NOMBRE"],
                      ["A001", "FIEBRES"],
                      ["A002", "DENGUE"],
                      ["A003", "VARICELA"]]
        self.xlsx = _xlsx_datos(self.filas)
        self.ruta_xlsx = os.path.join(base, "f.xlsx")
        with open(self.ruta_xlsx, "wb") as archivo:
            archivo.write(self.xlsx)
        import hashlib
        self.huella = hashlib.sha256(self.xlsx).hexdigest()
        self.catalogo = os.path.join(base, "fuentes.json")
        fuente = dict(FUENTE)
        fuente["verificaciones"] = [
            {"fecha": "2026-09-03", "resultado": "vigente",
             "huella": self.huella, "ruta_local": self.ruta_xlsx}]
        with open(self.catalogo, "w", encoding="utf-8") as archivo:
            json.dump({"version": 1, "fuentes": [fuente]}, archivo,
                      ensure_ascii=False)
        self.ruta_perfil = os.path.join(base, "perfiles",
                                        ID + ".json")
        self.servidor = crear_servidor(self.catalogo, "127.0.0.1", 0)
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

    def _pedir(self, ruta, encabezados=None, metodo="GET"):
        peticion = urllib.request.Request(
            self.base + ruta, headers=encabezados or {},
            method=metodo)
        try:
            with urllib.request.urlopen(peticion, timeout=10) as r:
                return (r.status, r.read(), dict(r.headers))
        except urllib.error.HTTPError as exc:
            return (exc.code, exc.read(), dict(exc.headers))

    def _json_datos(self, ruta="/fuentes/" + ID + "/datos"):
        codigo, cuerpo, _enc = self._pedir(ruta)
        return codigo, json.loads(cuerpo)

    def _escribir_perfil(self, perfil):
        os.makedirs(os.path.dirname(self.ruta_perfil), exist_ok=True)
        with open(self.ruta_perfil, "w", encoding="utf-8") as archivo:
            json.dump(perfil, archivo, ensure_ascii=False)
    def test_sin_perfil_filas_crudas(self):
        """DADO fuente sin perfil CUANDO GET /datos ENTONCES 200 con
        perfil_aplicado false, filas crudas y procedencia
        (sha256 vivo = registrado, verificado)."""
        codigo, cuerpo = self._json_datos()
        self.assertEqual(codigo, 200)
        self.assertFalse(cuerpo["perfil_aplicado"])
        hoja = cuerpo["hojas"]["Catalogo"]
        self.assertEqual(hoja["filas"], self.filas)
        self.assertEqual(cuerpo["procedencia"]["sha256"], self.huella)
        self.assertEqual(
            cuerpo["procedencia"]["estado_integridad"], "verificado")
        self.assertTrue(cuerpo["etag"])

    def test_con_perfil_segmenta_datos_y_totales(self):
        """DADO un perfil (encabezado fila 2, datos 3..5, total fila 1)
        CUANDO GET /datos ENTONCES datos segmentados, totales aparte
        y fuera_de_rango en cero."""
        self._escribir_perfil({
            "id": ID, "huella_base": self.huella,
            "fecha": "2026-09-03", "version_perfil": 1,
            "hojas": [{"nombre": "Catalogo", "tipo": "datos",
                       "fila_encabezados": 2,
                       "columnas": ["CLAVE", "NOMBRE"],
                       "filas_datos": {"desde": 3, "hasta": 5},
                       "clave_primaria": "CLAVE",
                       "filas_total": [1]}]})
        codigo, cuerpo = self._json_datos()
        self.assertEqual(codigo, 200)
        self.assertTrue(cuerpo["perfil_aplicado"])
        hoja = cuerpo["hojas"]["Catalogo"]
        self.assertEqual(hoja["encabezados"], ["CLAVE", "NOMBRE"])
        self.assertEqual(hoja["datos"], self.filas[2:5])
        self.assertEqual(hoja["totales"], [self.filas[0]])
        self.assertEqual(hoja["fuera_de_rango"], 0)
        self.assertFalse(hoja["requiere_revision"])

    def test_fuera_de_rango_requiere_revision(self):
        """DADO filas fuera del rango declarado (pérdida silenciosa,
        corrección adversarial #4) CUANDO GET /datos ENTONCES
        fuera_de_rango n>0 y requiere_revision true."""
        self._escribir_perfil({
            "id": ID, "huella_base": self.huella,
            "fecha": "2026-09-03", "version_perfil": 1,
            "hojas": [{"nombre": "Catalogo", "tipo": "datos",
                       "fila_encabezados": 2,
                       "columnas": ["CLAVE", "NOMBRE"],
                       "filas_datos": {"desde": 3, "hasta": 4},
                       "filas_total": [1]}]})
        _codigo, cuerpo = self._json_datos()
        hoja = cuerpo["hojas"]["Catalogo"]
        self.assertEqual(hoja["fuera_de_rango"], 1)
        self.assertTrue(hoja["requiere_revision"])
    def test_etag_compuesto_y_304(self):
        """DADO el ETag de una respuesta CUANDO se repite con
        If-None-Match ENTONCES 304 sin cuerpo; DADO perfil corregido
        con el MISMO archivo CUANDO se repite ENTONCES el ETag CAMBIA
        (la huella sola no basta — corrección adversarial #1)."""
        self._escribir_perfil({
            "id": ID, "huella_base": self.huella,
            "fecha": "2026-09-03", "version_perfil": 1,
            "hojas": [{"nombre": "Catalogo", "tipo": "datos",
                       "fila_encabezados": 2,
                       "columnas": ["CLAVE", "NOMBRE"],
                       "filas_datos": {"desde": 3, "hasta": 5}}]})
        codigo, _cuerpo, encabezados = self._pedir(
            "/fuentes/" + ID + "/datos")
        self.assertEqual(codigo, 200)
        etag = encabezados["ETag"]
        self.assertTrue(etag)
        self.assertEqual(encabezados["Cache-Control"],
                         "public, max-age=86400")
        self.assertEqual(
            encabezados["X-Content-Type-Options"], "nosniff")
        codigo_304, cuerpo_304, _enc = self._pedir(
            "/fuentes/" + ID + "/datos",
            encabezados={"If-None-Match": etag})
        self.assertEqual(codigo_304, 304)
        self.assertEqual(cuerpo_304, b"")
        # Corregir el perfil con el mismo archivo cambia el ETag.
        self._escribir_perfil({
            "id": ID, "huella_base": self.huella,
            "fecha": "2026-09-03", "version_perfil": 2,
            "hojas": [{"nombre": "Catalogo", "tipo": "datos",
                       "fila_encabezados": 2,
                       "columnas": ["CLAVE", "NOMBRE"],
                       "filas_datos": {"desde": 3, "hasta": 5}}]})
        _codigo, cuerpo2, enc2 = self._pedir(
            "/fuentes/" + ID + "/datos")
        self.assertNotEqual(enc2["ETag"], etag)

    def test_hoja_y_max_filas(self):
        """DADO hoja inexistente ENTONCES 404; DADO max_filas=1 con
        filas crudas ENTONCES truncado true; DADO max_filas inválido
        ENTONCES 400."""
        _codigo, _cuerpo = self._json_datos(
            "/fuentes/" + ID + "/datos?hoja=NoExiste")
        self.assertEqual(_codigo, 404)
        _codigo, cuerpo = self._json_datos(
            "/fuentes/" + ID + "/datos?max_filas=1")
        self.assertEqual(_codigo, 200)
        self.assertTrue(cuerpo["hojas"]["Catalogo"]["truncado"])
        self.assertEqual(len(cuerpo["hojas"]["Catalogo"]["filas"]), 1)
        codigo, _cuerpo = self._json_datos(
            "/fuentes/" + ID + "/datos?max_filas=abc")
        self.assertEqual(codigo, 400)

    def test_integridad_alterada_409(self):
        """DADO el archivo local alterado tras la verificación CUANDO
        GET /datos ENTONCES 409 (el dato nunca se sirve alterado)."""
        with open(self.ruta_xlsx, "ab") as archivo:
            archivo.write(b"basura")
        codigo, cuerpo = self._json_datos()
        self.assertEqual(codigo, 409)
        self.assertIn("integridad", cuerpo["error"])

    def test_head_sin_cuerpo(self):
        """DADO HEAD /datos CUANDO se atiende ENTONCES mismos
        encabezados (ETag) sin cuerpo."""
        codigo, cuerpo, encabezados = self._pedir(
            "/fuentes/" + ID + "/datos", metodo="HEAD")
        self.assertEqual(codigo, 200)
        self.assertEqual(cuerpo, b"")
        self.assertTrue(encabezados.get("ETag"))

    def test_mcp_datos_fuente(self):
        """DADO MCP inicializado CUANDO tools/call datos_fuente
        ENTONCES resultado JSON con hojas y sin isError."""
        cuerpo = {"jsonrpc": "2.0", "id": 7, "method": "tools/call",
                  "params": {"name": "datos_fuente",
                             "arguments": {"id": ID}}}
        peticion = urllib.request.Request(
            self.base + "/mcp",
            data=json.dumps(cuerpo).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST")
        with urllib.request.urlopen(peticion, timeout=10) as r:
            r = json.loads(r.read())
        resultado = r["result"]
        self.assertFalse(resultado["isError"])
        datos = json.loads(resultado["content"][0]["text"])
        self.assertEqual(datos["id"], ID)
        self.assertIn("Catalogo", datos["hojas"])


if __name__ == "__main__":
    unittest.main()
