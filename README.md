# Infosalud Nexus

Catálogo local de las fuentes de información de
[Infosalud](http://infosalud.imss.gob.mx/) — el portal oficial de la
División de Información en Salud (DIS), Coordinación de Información e
Inteligencia en Salud, Dirección de Prestaciones Médicas del IMSS.

**Consumidor primario: agentes de IA.** Humanos en segunda línea
(ADR-006). Sin red en la v1 (ADR-004): la herramienta nunca contacta
el portal; el humano descarga y la herramienta registra evidencia
(huella sha256, fecha).

## Documentación

- `docs/f0-analisis.md` — análisis y requerimientos (F0)
- `docs/f1-specs.md` — especificaciones (F1)
- `docs/f1-contratos.md` — contratos de frontera y máquina de estados
- `docs/adr/` — decisiones (ADR-001…006)

## Requisitos

- Python **3.13.5+** (`/opt/homebrew/bin/python3`, fórmula Homebrew
  `python@3.13`; ver ADR-001). Sólo biblioteca estándar: no hay
  dependencias que instalar ni build.

## Cómo correr

Desde la raíz del repositorio:

```bash
python3 -m infosalud --version
python3 -m infosalud fuente-lista            # texto plano (humano)
python3 -m infosalud fuente-lista --json     # JSON (agente, ADR-006)
python3 -m infosalud fuente-lista --seccion catalogos --formato xlsx
```

El catálogo vive en `data/fuentes.json` (contrato
`registro-de-fuente v1` en `docs/f1-contratos.md`).

## Cómo probar

```bash
python3 -m unittest discover -s tests -v
```

## Verificación local

```bash
python3 -m compileall -q infosalud && python3 -m unittest discover -s tests
```

## Límites de tamaño

Hereda los valores por defecto del estándar Skevi (ninguna
desviación declarada): 800 líneas por archivo de texto, 200 para
instrucciones de agentes (`AGENTS.md`), 300 para `README.md`.

## Sobre `skevi/`

El directorio `skevi/` es un clon de referencia del método
(github.com/kristhianmanue1/skevi), no código del proyecto: está en
`.gitignore` y sus normas se aplican por referencia (`AGENTS.md`
apunta a `skevi/docs/…`). No se copia al historial para no duplicar
un cuerpo normativo vivo.
