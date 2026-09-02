"""Tests F3 — traducen los casos DADO/CUANDO/ENTONCES de SPEC-1..3.

Cada test cita el caso de la spec que cubre (trazabilidad SPEC → test).
"""

import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _ejecutar(*argv):
    return subprocess.run(
        [sys.executable, "-m", "infosalud", *argv],
        capture_output=True, text=True, cwd=RAIZ,
    )


FUENTE_CIE10 = {
    "id": "catalogo-cie10",
    "seccion": "catalogos",
    "titulo": "Catálogo CIE-10",
    "url": "http://infosalud.imss.gob.mx/catalogos/cie10",
    "formato": "xlsx",
    "verificaciones": [],
}


def _catalogo_tmp(dir_tmp, fuentes=None):
    ruta = Path(dir_tmp) / "fuentes.json"
    ruta.write_text(json.dumps(
        {"version": 1, "fuentes": fuentes or []}), encoding="utf-8")
    return str(ruta)


def _archivo_tmp(dir_tmp, nombre, contenido):
    ruta = Path(dir_tmp) / nombre
    if not isinstance(contenido, str):
        contenido = json.dumps(contenido, ensure_ascii=False)
    ruta.write_text(contenido, encoding="utf-8")
    return str(ruta)


class TestFuenteAlta(unittest.TestCase):
    """SPEC-1: altas conforme a CONTRATO registro-de-fuente v1."""

    def setUp(self):
        self.dir_tmp = tempfile.mkdtemp()
        self.catalogo = _catalogo_tmp(self.dir_tmp)

    def test_alta_valida_agrega_al_catalogo(self):
        fuente = _archivo_tmp(self.dir_tmp, "fuente.json", FUENTE_CIE10)
        r = _ejecutar("fuente-alta", "--catalogo", self.catalogo,
                      "--archivo", fuente)
        self.assertEqual(r.returncode, 0, r.stderr)
        lista = json.loads(_ejecutar(
            "fuente-lista", "--catalogo", self.catalogo,
            "--json").stdout)
        self.assertEqual(lista["fuentes"][0]["id"], "catalogo-cie10")

    def test_alta_sin_url_rechaza_con_campo_y_motivo(self):
        # DADO un alta sin campo url ENTONCES se rechaza nombrando el
        # campo y el catálogo queda sin cambios.
        fuente = dict(FUENTE_CIE10)
        del fuente["url"]
        ruta = _archivo_tmp(self.dir_tmp, "sin-url.json", fuente)
        r = _ejecutar("fuente-alta", "--catalogo", self.catalogo,
                      "--archivo", ruta)
        self.assertEqual(r.returncode, 1)
        self.assertIn("url", r.stderr)
        lista = json.loads(_ejecutar(
            "fuente-lista", "--catalogo", self.catalogo, "--json").stdout)
        self.assertEqual(lista["fuentes"], [])

    def test_alta_duplicada_rechaza_sin_cambios(self):
        # DADO un id ya existente ENTONCES rechaza y queda sin cambios.
        fuente = _archivo_tmp(self.dir_tmp, "fuente.json", FUENTE_CIE10)
        _ejecutar("fuente-alta", "--catalogo", self.catalogo,
                  "--archivo", fuente)
        r = _ejecutar("fuente-alta", "--catalogo", self.catalogo,
                      "--archivo", fuente)
        self.assertEqual(r.returncode, 1)
        self.assertIn("id", r.stderr)
        lista = json.loads(_ejecutar(
            "fuente-lista", "--catalogo", self.catalogo, "--json").stdout)
        self.assertEqual(len(lista["fuentes"]), 1)

    def test_alta_url_fuera_de_imss_rechaza(self):
        # El contrato cierra el dominio: host *.imss.gob.mx.
        fuente = dict(FUENTE_CIE10, url="https://ejemplo.org/x")
        ruta = _archivo_tmp(self.dir_tmp, "otro-host.json", fuente)
        r = _ejecutar("fuente-alta", "--catalogo", self.catalogo,
                      "--archivo", ruta)
        self.assertEqual(r.returncode, 1)
        self.assertIn("url", r.stderr)


    def test_alta_url_con_puerto_aceptada(self):
        # El portal sirve archivos en infosalud.imss.gob.mx:8080;
        # el contrato valida el host, el puerto se ignora.
        fuente = dict(FUENTE_CIE10,
                      url="http://infosalud.imss.gob.mx:8080/ARCHIVOS/x.xlsx")
        ruta = _archivo_tmp(self.dir_tmp, "con-puerto.json", fuente)
        r = _ejecutar("fuente-alta", "--catalogo", self.catalogo,
                      "--archivo", ruta)
        self.assertEqual(r.returncode, 0, r.stderr)


class TestFuenteBuscar(unittest.TestCase):
    """SPEC-1: localizar por término en menos de 2 segundos."""

    def setUp(self):
        self.dir_tmp = tempfile.mkdtemp()
        self.catalogo = _catalogo_tmp(self.dir_tmp, [FUENTE_CIE10])

    def test_busqueda_encuentra_en_menos_de_2s(self):
        # DADO una fuente "catalogo-cie10" CUANDO busco "cie10"
        # ENTONCES aparece en menos de 2 segundos.
        inicio = time.monotonic()
        r = _ejecutar("fuente-buscar", "cie10",
                      "--catalogo", self.catalogo, "--json")
        transcurrido = time.monotonic() - inicio
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertLess(transcurrido, 2.0)
        self.assertIn("catalogo-cie10", r.stdout)

    def test_busqueda_sin_resultados_sale_2(self):
        r = _ejecutar("fuente-buscar", "zzz-inexistente",
                      "--catalogo", self.catalogo)
        self.assertEqual(r.returncode, 2)


class TestFuenteDetalle(unittest.TestCase):
    """SPEC-1: del registro a la información original en 2 pasos."""

    def test_detalle_muestra_url_en_un_comando(self):
        dir_tmp = tempfile.mkdtemp()
        catalogo = _catalogo_tmp(dir_tmp, [FUENTE_CIE10])
        r = _ejecutar("fuente-detalle", "catalogo-cie10",
                      "--catalogo", catalogo, "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(
            json.loads(r.stdout)["fuente"]["url"], FUENTE_CIE10["url"])

    def test_detalle_id_inexistente_sale_2(self):
        dir_tmp = tempfile.mkdtemp()
        r = _ejecutar("fuente-detalle", "no-existe",
                      "--catalogo", _catalogo_tmp(dir_tmp))
        self.assertEqual(r.returncode, 2)

class TestVigenciaRegistrar(unittest.TestCase):
    """SPEC-2 y máquina de estados de vigencia."""

    def setUp(self):
        self.dir_tmp = tempfile.mkdtemp()
        self.catalogo = _catalogo_tmp(self.dir_tmp, [FUENTE_CIE10])
        self.archivo_a = _archivo_tmp(
            self.dir_tmp, "cie10-v1.xlsx", "contenido version 1")

    def _registrar(self, ruta_archivo):
        return _ejecutar("vigencia-registrar", "catalogo-cie10",
                         "--catalogo", self.catalogo,
                         "--archivo", ruta_archivo, "--json")

    def test_primera_verificacion_vigente(self):
        # DADO sin verificación previa CUANDO registro con huella H
        # ENTONCES el estado es vigente.
        r = self._registrar(self.archivo_a)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["resultado"], "vigente")

    def test_misma_huella_vigente(self):
        self._registrar(self.archivo_a)
        r = self._registrar(self.archivo_a)
        self.assertEqual(json.loads(r.stdout)["resultado"], "vigente")

    def test_huella_distinta_cambiada(self):
        # DADO huella previa H CUANDO el archivo presenta huella
        # distinta ENTONCES el estado es cambiada.
        self._registrar(self.archivo_a)
        archivo_b = _archivo_tmp(
            self.dir_tmp, "cie10-v2.xlsx", "contenido version 2")
        r = self._registrar(archivo_b)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["resultado"], "cambiada")

    def test_archivo_inexistente_inaccesible_fallo_explicito(self):
        # DADO una ruta inexistente ENTONCES el estado es inaccesible,
        # se registra como fallo (exit 1) y nunca como éxito.
        r = self._registrar("/tmp/no-existe-xyz-123.xlsx")
        self.assertEqual(r.returncode, 1)
        historia = json.loads(_ejecutar(
            "vigencia-historia", "catalogo-cie10",
            "--catalogo", self.catalogo, "--json").stdout)
        self.assertEqual(
            historia["verificaciones"][-1]["resultado"], "inaccesible")

    def test_id_inexistente_sale_2(self):
        r = _ejecutar("vigencia-registrar", "no-existe",
                      "--catalogo", self.catalogo,
                      "--archivo", self.archivo_a)
        self.assertEqual(r.returncode, 2)


class TestVigenciaHistoria(unittest.TestCase):
    """SPEC-2: historial append-only cronológico con trazabilidad."""

    def test_historial_cronologico_completo(self):
        dir_tmp = tempfile.mkdtemp()
        catalogo = _catalogo_tmp(dir_tmp, [FUENTE_CIE10])
        a = _archivo_tmp(dir_tmp, "a.xlsx", "v1")
        b = _archivo_tmp(dir_tmp, "b.xlsx", "v2")
        _ejecutar("vigencia-registrar", "catalogo-cie10",
                  "--catalogo", catalogo, "--archivo", a)
        _ejecutar("vigencia-registrar", "catalogo-cie10",
                  "--catalogo", catalogo, "--archivo", b)
        r = _ejecutar("vigencia-historia", "catalogo-cie10",
                      "--catalogo", catalogo, "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        verificaciones = json.loads(r.stdout)["verificaciones"]
        self.assertEqual(len(verificaciones), 2)
        self.assertEqual([v["resultado"] for v in verificaciones],
                         ["vigente", "cambiada"])
        for v in verificaciones:
            # REQ-8: toda verificación lleva fecha (trazabilidad).
            self.assertIn("fecha", v)


class TestSinRed(unittest.TestCase):
    """SPEC-3 / ADR-004 / ADR-008: la red vive sólo en infosalud.red.

    ADR-008 (REQ-6) autorizó un único camino de red de sólo lectura
    (vigencia-verificar). La guarda exige que cargar los módulos sin
    ese comando no toque librerías de red, y que si se cargan, sea
    porque infosalud.red (el único módulo autorizado) fue importado.
    """

    def test_catalogo_y_vigencia_no_importan_librerias_de_red(self):
        codigo = (
            "import sys; import infosalud.catalogo, infosalud.vigencia; "
            "prohibidos = {'socket', 'urllib', 'http', 'ftplib', "
            "'smtplib', 'ssl'}; "
            "cargados = prohibidos & set(sys.modules); "
            "assert not cargados, cargados"
        )
        r = subprocess.run([sys.executable, "-c", codigo],
                           capture_output=True, text=True, cwd=RAIZ)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_red_de_cli_esta_concentrada_en_infosalud_red(self):
        codigo = (
            "import sys; import infosalud.cli; "
            "prohibidos = {'socket', 'urllib', 'http', 'ftplib', "
            "'smtplib', 'ssl'}; "
            "cargados = prohibidos & set(sys.modules); "
            "assert not cargados or 'infosalud.red' in sys.modules, "
            "cargados"
        )
        r = subprocess.run([sys.executable, "-c", codigo],
                           capture_output=True, text=True, cwd=RAIZ)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_solo_infosalud_red_importa_librerias_de_red(self):
        """Ningún módulo de infosalud salvo red.py (red saliente,
        ADR-008) y servicio.py (servidor de lectura, ADR-013) importa
        urllib/http/socket directamente (barrido estático)."""
        paquete = Path("infosalud")
        exentos = {"red.py", "servicio.py"}
        for ruta in paquete.glob("*.py"):
            texto = ruta.read_text(encoding="utf-8")
            if ruta.name in exentos:
                continue
            for prohibido in ("urllib", "import socket", "import http",
                              "import ssl"):
                self.assertNotIn(prohibido, texto,
                                 f"{ruta.name} importa {prohibido}")


class TestEscrituraAtomica(unittest.TestCase):
    """SPEC-3: escrituras atómicas, catálogo nunca a medias."""

    def test_guardado_no_deja_temporales_y_catalogo_valido(self):
        dir_tmp = tempfile.mkdtemp()
        catalogo = _catalogo_tmp(dir_tmp, [FUENTE_CIE10])
        archivo = _archivo_tmp(dir_tmp, "a.xlsx", "v1")
        r = _ejecutar("vigencia-registrar", "catalogo-cie10",
                      "--catalogo", catalogo, "--archivo", archivo)
        self.assertEqual(r.returncode, 0, r.stderr)
        residuos = list(Path(dir_tmp).glob("*.tmp"))
        self.assertEqual(residuos, [])
        with open(catalogo, encoding="utf-8") as f:
            json.load(f)  # el catálogo quedó parseable (íntegro)


class TestEsquemaCerrado(unittest.TestCase):
    """Hallazgos adversariales: el esquema es cerrado y 'verificaciones'
    inicia vacía (CONTRATO registro-de-fuente v1)."""

    def setUp(self):
        self.dir_tmp = tempfile.mkdtemp()
        self.catalogo = _catalogo_tmp(self.dir_tmp)

    def test_campo_no_declarado_rechazado(self):
        fuente = dict(FUENTE_CIE10, payload_opaco={"inyectado": True})
        ruta = _archivo_tmp(self.dir_tmp, "extra.json", fuente)
        r = _ejecutar("fuente-alta", "--catalogo", self.catalogo,
                      "--archivo", ruta)
        self.assertEqual(r.returncode, 1)
        self.assertIn("payload_opaco", r.stderr)
        lista = json.loads(_ejecutar(
            "fuente-lista", "--catalogo", self.catalogo, "--json").stdout)
        self.assertEqual(lista["fuentes"], [])

    def test_verificaciones_precargadas_rechazadas(self):
        # El contrato: "inicia vacía"; una huella "ZZ" pre-cargada
        # gobernaría la máquina de estados.
        fuente = dict(FUENTE_CIE10, verificaciones=[
            {"fecha": "no-es-fecha", "resultado": "BOGUS", "huella": "ZZ"},
        ])
        ruta = _archivo_tmp(self.dir_tmp, "prehist.json", fuente)
        r = _ejecutar("fuente-alta", "--catalogo", self.catalogo,
                      "--archivo", ruta)
        self.assertEqual(r.returncode, 1)
        self.assertIn("verificaciones", r.stderr)


class TestCodigosDeSalida(unittest.TestCase):
    """Hallazgo adversarial HIGH: argparse usaba 2 (E-NOEXISTE) para
    errores de uso; el contrato reserva 2 para 'no encontrado'."""

    def test_uso_invalido_sale_1(self):
        r = _ejecutar("fuente-alta")  # falta --archivo obligatorio
        self.assertEqual(r.returncode, 1)


class TestSalidaJsonEnErrores(unittest.TestCase):
    """Hallazgo adversarial MED: con --json, 'un objeto por ejecución'
    incluye los fallos (clave 'error' en stdout, diagnóstico en stderr)."""

    def test_error_en_modo_json_emite_objeto_parseable(self):
        dir_tmp = tempfile.mkdtemp()
        catalogo = _catalogo_tmp(dir_tmp, [FUENTE_CIE10])
        r = _ejecutar("vigencia-registrar", "catalogo-cie10",
                      "--catalogo", catalogo,
                      "--archivo", "/tmp/no-existe-xyz-123.xlsx", "--json")
        self.assertEqual(r.returncode, 1)
        salida = json.loads(r.stdout)  # debe ser parseable
        self.assertIn("error", salida)
        self.assertIn("ERROR", r.stderr)


class TestCausaInaccesible(unittest.TestCase):
    """Hallazgo adversarial HIGH: 'inaccesible' registra la causa."""

    def test_inaccesible_persiste_la_causa(self):
        dir_tmp = tempfile.mkdtemp()
        catalogo = _catalogo_tmp(dir_tmp, [FUENTE_CIE10])
        r = _ejecutar("vigencia-registrar", "catalogo-cie10",
                      "--catalogo", catalogo, "--archivo", dir_tmp)
        self.assertEqual(r.returncode, 1)  # un directorio no es legible
        historia = json.loads(_ejecutar(
            "vigencia-historia", "catalogo-cie10",
            "--catalogo", catalogo, "--json").stdout)
        ultima = historia["verificaciones"][-1]
        self.assertEqual(ultima["resultado"], "inaccesible")
        self.assertTrue(ultima.get("causa"))


class TestSalidaAlta(unittest.TestCase):
    """Hallazgo adversarial MED: la salida del alta es el registro
    almacenado, idéntico al validado (CONTRATO registro-de-fuente v1)."""

    def test_alta_devuelve_el_registro_almacenado(self):
        dir_tmp = tempfile.mkdtemp()
        catalogo = _catalogo_tmp(dir_tmp)
        ruta = _archivo_tmp(dir_tmp, "fuente.json", FUENTE_CIE10)
        r = _ejecutar("fuente-alta", "--catalogo", catalogo,
                      "--archivo", ruta, "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        salida = json.loads(r.stdout)
        self.assertEqual(salida["alta"], "ok")
        self.assertEqual(salida["fuente"], FUENTE_CIE10)


class TestBusquedaVacia(unittest.TestCase):
    """Hallazgo adversarial LOW: término vacío no está declarado;
    se rechaza como E-VALID."""

    def test_termino_vacio_rechazado(self):
        r = _ejecutar("fuente-buscar", "")
        self.assertEqual(r.returncode, 1)


class TestEscrituraInterrumpida(unittest.TestCase):
    """SPEC-3: si la escritura falla, el catálogo anterior queda
    íntegro (el test original no interrumpía nada)."""

    def test_fallo_de_escritura_deja_el_anterior_igulo(self):
        from unittest.mock import patch
        from infosalud import catalogo as modulo
        dir_tmp = tempfile.mkdtemp()
        ruta = Path(dir_tmp) / "fuentes.json"
        datos_previos = {"version": 1, "fuentes": [dict(FUENTE_CIE10)]}
        ruta.write_text(json.dumps(datos_previos), encoding="utf-8")
        with patch.object(Path, "write_text",
                          side_effect=OSError("disco lleno simulado")):
            with self.assertRaises(OSError):
                modulo.guardar_catalogo(ruta, {"version": 1, "fuentes": []})
        # El catálogo anterior quedó íntegro.
        self.assertEqual(json.loads(ruta.read_text(encoding="utf-8")),
                         datos_previos)


if __name__ == "__main__":
    unittest.main()

