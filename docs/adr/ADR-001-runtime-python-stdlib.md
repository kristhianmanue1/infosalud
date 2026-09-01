# ADR-001: Python 3.13 con biblioteca estándar únicamente

Estado: aceptado (implementación no iniciada)
Fecha: 2026-09-01

Contexto: REQ-7 (operación local sin internet) y restricción R2 de
`docs/f0-analisis.md`. Hay dos runtimes disponibles en el host
(EV-1, EV-2) y debe elegirse lenguaje y política de dependencias
antes del cascarón (F2).

Decisión: la v1 se escribe en Python 3.13 usando sólo la biblioteca
estándar (json, hashlib, argparse, pathlib, unittest).

Alternativas descartadas:
  - Node.js 22: capacidad equivalente para el alcance v1, pero sin
    ventaja concreta; el criterio de desempate (sin dependencias
    nuevas, menor superficie) no lo favorece.
  - Contenedor Docker: aísla, pero el host es dedicado al proyecto y
    añade superficie de mantenimiento sin requisito que lo pida.
  - Dependencias de terceros (pandas, openpyxl): cubrirían el
    parsing de Excel, pero violan "sin dependencias nuevas" sin
    requisito v1 que exija parsear xlsx (los catálogos se
    referencian y copian, no se parsean; ver Consecuencias).

Consecuencias: gana simplicidad (cero instalación, cero build) y
reversibilidad. Pierde lectura nativa de .xlsx: si un REQ futuro
exige parsear Excel, se crea un ADR nuevo que justifique la
dependencia. Queda prohibido importar paquetes fuera de la stdlib
en la v1 sin nuevo ADR.

Fijación de runtime (2026-09-01, verificación F2):
- Intérprete fijado: /opt/homebrew/bin/python3 → fórmula Homebrew
  `python@3.13`, versión 3.13.5.
- Evidencia: `ls -la /opt/homebrew/bin/python3` → symlink a
  ../Cellar/python@3.13/3.13.5/bin/python3; `python3 --version` →
  Python 3.13.5.
- Nota: python@3.12 (3.12.11) también está instalado en el host;
  el proyecto fija 3.13.5 como mínimo (`requires-python >=3.13`
  en pyproject.toml). El recuerdo de "estábamos en 3.12" era
  correcto como versión coexistente, no como la activa.
