# AGENTS.md — Infosalud Nexus

Punto de entrada para agentes de IA que trabajen en este proyecto.
El consumidor primario del sistema es un agente de IA (ADR-006);
las reglas de operación lo reflectan.

## Comandos reales (verificados en F2)

```bash
# correr
python3 -m infosalud --version
python3 -m infosalud fuente-lista --json

# probar
python3 -m unittest discover -s tests -v

# verificación local completa (build + test)
python3 -m compileall -q infosalud && python3 -m unittest discover -s tests
```

Runtime fijado: Python 3.13.5, Homebrew `python@3.13` (ADR-001).
Sólo biblioteca estándar: `dependencies = []` en `pyproject.toml`.

## Convenciones

- Markdown y español; líneas de ~80 columnas.
- Los contratos de `docs/f1-contratos.md` son norma: se acepta lo
  declarado, se rechaza lo demás; un cambio incompatible exige
  subir versión del contrato.
- Toda decisión con alternativas reales crea un ADR en `docs/adr/`
  (inmutables: cambiar una decisión crea un ADR nuevo).
- Los casos DADO/CUANDO/ENTONCES de `docs/f1-specs.md` se traducen
  a tests en `tests/`.

## Prohibido

- Cualquier comunicación de red desde el código (ADR-004): la v1
  no abre sockets ni descarga nada.
- Dependencias fuera de la stdlib sin ADR nuevo que lo justifique.
- Datos personales: sólo totales agregados (REQ-9 de
  `docs/f0-analisis.md`).
- `git push`, merges, tags, releases y operaciones destructivas:
  requieren autorización humana explícita, una por una.
- Trabajar directo sobre la rama principal; usar ramas
  `tipo/descripcion-corta`.

## Límites de tamaño

Heredados del estándar (sin desviaciones): 800 líneas por archivo
de texto; 200 para este archivo; 300 para `README.md`. Comprobar
con conteo, nunca a ojo.

<!-- skevi:registry:start -->
[skevi]
usage        = .skevi/usage-guide.md
architecture = .skevi/architecture-overview.md
standard     = skevi/docs/estandar-diseno-software-github.md
guide        = skevi/docs/ai-agent-guide/00-INDICE.md
<!-- skevi:registry:end -->
