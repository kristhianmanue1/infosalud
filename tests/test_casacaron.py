"""Tests del cascarón F2 — verifican el contrato cli-infosalud v1.1."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _ejecutar(*argv):
    return subprocess.run(
        [sys.executable, "-m", "infosalud", *argv],
        capture_output=True, text=True, cwd=RAIZ,
    )


class TestVersion(unittest.TestCase):
    def test_version_reporta_0_1_0(self):
        resultado = _ejecutar("--version")
        self.assertEqual(resultado.returncode, 0)
        self.assertIn("0.1.0", resultado.stdout)


class TestFuenteLista(unittest.TestCase):
    def test_catalogo_vacio_lista_cero_fuentes(self):
        # El test usa un catálogo temporal: no debe depender del
        # contenido del catálogo del repositorio (data/fuentes.json).
        with tempfile.NamedTemporaryFile(
                "w", suffix=".json", delete=False) as archivo:
            json.dump({"version": 1, "fuentes": []}, archivo)
            ruta = archivo.name
        resultado = _ejecutar(
            "fuente-lista", "--catalogo", ruta, "--json")
        self.assertEqual(resultado.returncode, 0)
        salida = json.loads(resultado.stdout)
        self.assertEqual(salida, {"fuentes": []})
        Path(ruta).unlink()

    def test_filtro_por_formato_devuelve_coincidencias(self):
        with tempfile.NamedTemporaryFile(
                "w", suffix=".json", delete=False) as archivo:
            json.dump({
                "version": 1,
                "fuentes": [{
                    "id": "catalogo-cie10",
                    "seccion": "catalogos",
                    "titulo": "Catálogo CIE-10",
                    "url": "http://infosalud.imss.gob.mx/cie10",
                    "formato": "xlsx",
                    "verificaciones": [],
                }],
            }, archivo)
            ruta = archivo.name
        resultado = _ejecutar(
            "fuente-lista", "--catalogo", ruta, "--formato", "xlsx")
        self.assertEqual(resultado.returncode, 0)
        self.assertIn("catalogo-cie10", resultado.stdout)
        Path(ruta).unlink()

    def test_catalogo_inexistente_falla_controlado(self):
        resultado = _ejecutar(
            "fuente-lista", "--catalogo", "/tmp/no-existe-xyz.json")
        self.assertEqual(resultado.returncode, 1)
        self.assertIn("ERROR", resultado.stderr)


if __name__ == "__main__":
    unittest.main()
