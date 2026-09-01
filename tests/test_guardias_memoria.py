"""Guardias de memoria: integridad de AGENTS.md/AN-KLA.md y del
bloque gestionado an-kla. Nace del bug real de fence sin cerrar
(2026-09-01, ADR-007).

División honesta (ronda adversarial F3-04):
- TestFencesBalanceados: stdlib-only, corre en cualquier máquina.
- TestBloqueGestionado: requiere .venv con an_kla; se salta con
  degradación declarada si el venv no existe (clone fresco).
"""

import json
import os
import re
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _fences_balanceados(ruta):
    """Replica el conteo de fences de an_kla.context_package."""
    fence = None
    with open(ruta, encoding="utf-8") as archivo:
        for numero, linea in enumerate(archivo, 1):
            m = re.match(r"(`{3,}|~{3,})", linea.lstrip())
            if m:
                token = m.group(1)
                if fence is None:
                    fence = (token[0], len(token))
                elif fence[0] == token[0] and len(token) >= fence[1]:
                    fence = None
                else:
                    return f"línea {numero}: fence sin cerrar previo {fence}"
    return None if fence is None else f"EOF con fence abierto: {fence}"


class TestFencesBalanceados(unittest.TestCase):
    """Guard duro stdlib-only: sin fences abiertos, los marcadores
    an-kla nunca quedan 'dentro de un fence' (fail-closed del
    validador de an-kla)."""

    def test_agents_md_y_an_kla_md_sin_fences_abiertos(self):
        for nombre in ("AGENTS.md", "AN-KLA.md"):
            resultado = _fences_balanceados(os.path.join(RAIZ, nombre))
            self.assertIsNone(resultado, f"{nombre}: {resultado}")

    def test_agents_md_tiene_exactamente_un_par_de_marcadores(self):
        with open(os.path.join(RAIZ, "AGENTS.md"), encoding="utf-8") as f:
            lineas = f.readlines()
        begins = [l for l in lineas if l.startswith("<!-- an-kla:managed-begin ")]
        ends = [l for l in lineas if l.startswith("<!-- an-kla:managed-end ")]
        self.assertEqual(len(begins), 1)
        self.assertEqual(len(ends), 1)


@unittest.skipUnless(
    os.path.exists(os.path.join(RAIZ, ".venv", "bin", "python")),
    "degradación declarada: .venv ausente (clone fresco); "
    "corre scripts/hooks/instalar.sh — ADR-007")
class TestBloqueGestionado(unittest.TestCase):
    """Con an_kla disponible: el bloque gestionado debe validar."""

    def test_context_status_instalado_y_ok(self):
        import subprocess
        entorno = dict(os.environ, AN_KLA_NO_UPDATE_CHECK="1")
        r = subprocess.run(
            [os.path.join(RAIZ, ".venv", "bin", "python"), "-m", "an_kla",
             "--no-update-check", "--project-root", RAIZ,
             "context", "status"],
            capture_output=True, text=True, env=entorno, cwd=RAIZ)
        self.assertEqual(r.returncode, 0, r.stderr)
        estado = json.loads(r.stdout)
        self.assertTrue(estado["installed"],
                        f"diagnósticos: {estado.get('diagnostics')}")
        self.assertTrue(estado["ok"],
                        f"diagnósticos: {estado.get('diagnostics')}")


if __name__ == "__main__":
    unittest.main()
