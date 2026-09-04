# Infosalud Nexus

Catálogo local de las fuentes de información de
[Infosalud](http://infosalud.imss.gob.mx/) — el portal oficial de la
División de Información en Salud (DIS), Coordinación de Información e
Inteligencia en Salud, Dirección de Prestaciones Médicas del IMSS.

**Consumidor primario: agentes de IA.** Humanos en segunda línea
(ADR-006). Red mínima: sólo `vigencia-verificar` hace GET de sólo
lectura al portal (ADR-008); lo demás opera sin red. La herramienta
registra evidencia (huella sha256, fecha, estructura observada).

## Documentación

- `docs/f0-analisis.md` — análisis y requerimientos (F0)
- `docs/f1-specs.md` — especificaciones (F1)
- `docs/f1-contratos.md` — contratos de frontera y máquina de estados
- `docs/INDICE.md` — índice navegable de toda la documentación (ruta de lectura para agentes)
- `docs/adr/` — decisiones inmutables (ADR-001…015)
- `docs/diagramas.md`, `docs/operaciones.md`, `docs/glosario.md`, `docs/auditoria-documentacion.md` — arquitectura visual, runbook y glosario

## Requisitos

- Python **3.13.5+** (`/opt/homebrew/bin/python3`, fórmula Homebrew
  `python@3.13`; ver ADR-001). Sólo biblioteca estándar: no hay
  dependencias que instalar ni build.

## Cómo correr

Desde la raíz del repositorio:

```bash
python3 -m infosalud --version
python3 -m infosalud fuente-alta --archivo fuente.json
python3 -m infosalud fuente-lista                     # texto (humano)
python3 -m infosalud fuente-lista --json              # JSON (agente)
python3 -m infosalud fuente-buscar cie10
python3 -m infosalud fuente-detalle catalogo-cie10
python3 -m infosalud fuente-campos catalogo-cie10     # diccionario de datos (ADR-009)
python3 -m infosalud fuente-exportar catalogo-cie10  # CSV/SQLite con evidencia (ADR-011)
python3 -m infosalud vigencia-registrar catalogo-cie10 --archivo cie10.xlsx
python3 -m infosalud vigencia-verificar catalogo-cie10  # descarga read-only (ADR-008)
python3 -m infosalud vigencia-historia catalogo-cie10
python3 -m infosalud auditoria-estructura catalogo-cie10  # ADR-014
```

Todos los comandos aceptan `--catalogo <ruta>` (por defecto
`data/fuentes.json`) y `--json` (contrato `cli-infosalud v1.1`,
ADR-006). Códigos de salida: 0 éxito, 1 error de validación, 2 no
encontrado. Los perfiles estructurales viven en `data/perfiles/` y las
dimensiones canónicas en `data/dimensiones.json` (contrato
`dimension-v1`). El esquema del registro está en `docs/f1-contratos.md`
(`registro-de-fuente v1`); el diccionario de datos, en
`diccionario-de-fuente v1` (`data/diccionarios/<id>.json`, ADR-009).

## Servicio para agentes (v2, ADR-013)

```bash
python3 -m infosalud servir                    # http://127.0.0.1:8081
python3 -m infosalud servir --host <ip-intranet> --puerto 8081
INFOSALUD_SERVICIO_TOKEN=... python3 -m infosalud servir
```

API JSON de sólo lectura (`/`, `/healthz`, `/fuentes`,
`/fuentes/{id}`, `/fuentes/{id}/campos`, `/fuentes/{id}/historia`,
`/fuentes/{id}/archivo` —binario verificado—,
`/fuentes/{id}/archivo/meta`, `/fuentes/{id}/datos`,
`/fuentes/{id}/exportar`) y MCP
(JSON-RPC 2.0 en `POST /mcp`, 10 herramientas). Sólo stdlib; no muta
el catálogo ni descarga del portal (contrato `servicio-infosalud v1`).


## Contenedor (OrbStack/Docker)

```bash
docker compose up -d --build   # contenedor 1nf0541ud, restart: always
```

`data/` se monta como volumen; el servicio queda permanente en el
puerto 8081 de todas las interfaces (ADR-013).

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

## Política de CI (obligatoria para agentes)

**Sin CI de GitHub sin autorización del usuario.** Los gates corren
localmente (hooks de Git + `unittest`); este repositorio no define
workflows de GitHub Actions y ningún agente debe añadirlos ni
depender de ellos. El push se realiza con `gh` del administrador
**sin disparar CI**. Ver `AGENTS.md` §Prohibido.

## Sobre `skevi/`

El directorio `skevi/` es un clon de referencia del método
(github.com/kristhianmanue1/skevi), no código del proyecto: está en
`.gitignore` y sus normas se aplican por referencia (`AGENTS.md`
apunta a `skevi/docs/…`). No se copia al historial para no duplicar
un cuerpo normativo vivo.
