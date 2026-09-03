"""SPEC-10 (ADR-015): lock de catálogo para escritores concurrentes.

Casos DADO/CUANDO/ENTONCES:
- El lock es exclusivo: un segundo adquirente espera o falla acotado.
- Vencida la espera: ErrorCatalogo, catálogo sin cambios (fail-closed).
- Dos altas concurrentes de ids distintos: ambas quedan (regresión
  del incidente 2026-09-02, donde last-writer-wins perdió un alta).
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from infosalud.catalogo import ErrorCatalogo, bloque_catalogo

RAIZ = Path(__file__).resolve().parent.parent
FUENTE_MINIMA = {
    "id": "fuente-prueba",
    "seccion": "catalogos",
    "titulo": "Fuente de prueba",
    "url": "https://infosalud.imss.gob.mx/archivos/prueba.xlsx",
    "formato": "xlsx",
    "verificaciones": [],
}


class PruebaBloqueCatalogo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ruta = Path(self.tmp.name) / "fuentes.json"
        self.ruta.write_text(
            json.dumps({"version": 1, "fuentes": []}),
            encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_excluye_segundo_adquirente(self):
        """DADO el lock tomado CUANDO otro intenta con espera corta
        ENTONCES ErrorCatalogo, sin escribir (fail-closed)."""
        with bloque_catalogo(self.ruta, espera=5):
            with self.assertRaises(ErrorCatalogo):
                with bloque_catalogo(self.ruta, espera=0.1):
                    pass
            # El catálogo queda íntegro y sin cambios.
            self.assertEqual(json.loads(
                self.ruta.read_text(encoding="utf-8")),
                {"version": 1, "fuentes": []})

    def test_se_libera_al_salir(self):
        """DADO el lock liberado CUANDO otro adquiere ENTONCES
        procede de inmediato."""
        with bloque_catalogo(self.ruta, espera=1):
            pass
        with bloque_catalogo(self.ruta, espera=1):
            pass  # sin excepción: el lock fue liberado

    def test_archivo_lock_persiste(self):
        """DADO un uso del lock CUANDO se libera ENTONCES el archivo
        lateral no se borra (evita la carrera de unlink)."""
        with bloque_catalogo(self.ruta, espera=1):
            pass
        self.assertTrue(
            self.ruta.with_name(self.ruta.name + ".lock").is_file())

    def _alta_subproceso(self, id_fuente):
        fuente = dict(FUENTE_MINIMA, id=id_fuente)
        ruta_fuente = Path(self.tmp.name) / f"{id_fuente}.json"
        ruta_fuente.write_text(
            json.dumps(fuente), encoding="utf-8")
        entorno = dict(os.environ, INFOSALUD_LOCK_ESPERA="10")
        return subprocess.Popen(
            [sys.executable, "-m", "infosalud", "fuente-alta",
             "--catalogo", str(self.ruta),
             "--archivo", str(ruta_fuente)],
            cwd=RAIZ, env=entorno,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def test_altas_concurrentes_no_se_pierden(self):
        """DADO dos altas simultáneas de ids distintos ENTONCES ambas
        quedan en el catálogo (regresión del incidente 2026-09-02:
        antes el último guardado pisaba al anterior)."""
        procesos = [self._alta_subproceso(f"fuente-{n}")
                    for n in range(2)]
        codigos = [p.wait() for p in procesos]
        self.assertEqual(codigos, [0, 0])
        catalogo = json.loads(
            self.ruta.read_text(encoding="utf-8"))
        ids = {f["id"] for f in catalogo["fuentes"]}
        self.assertEqual(ids, {"fuente-0", "fuente-1"})

    def test_alta_bajo_lock_ajeno_falla_acotada(self):
        """DADO el lock tomado por otro proceso CUANDO fuente-alta
        con espera corta ENTONCES salida 1 y catálogo sin cambios."""
        entorno = dict(os.environ, INFOSALUD_LOCK_ESPERA="0.2")
        fuente = dict(FUENTE_MINIMA, id="fuente-fuera")
        ruta_fuente = Path(self.tmp.name) / "fuente-fuera.json"
        ruta_fuente.write_text(json.dumps(fuente), encoding="utf-8")
        with bloque_catalogo(self.ruta, espera=5):
            resultado = subprocess.run(
                [sys.executable, "-m", "infosalud", "fuente-alta",
                 "--catalogo", str(self.ruta),
                 "--archivo", str(ruta_fuente)],
                cwd=RAIZ, env=entorno, capture_output=True,
                text=True)
        self.assertEqual(resultado.returncode, 1)
        self.assertIn("bloqueado", resultado.stderr)
        catalogo = json.loads(
            self.ruta.read_text(encoding="utf-8"))
        self.assertEqual(catalogo["fuentes"], [])


if __name__ == "__main__":
    unittest.main()
