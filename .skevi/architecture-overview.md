# Arquitectura propuesta — puntero

**Estado:** con ADRs — F1 cerrada el 2026-09-01.

## ADRs del proyecto

- `docs/adr/ADR-001-runtime-python-stdlib.md` — Python 3.13.5
  (Homebrew), sólo stdlib; sin dependencias.
- `docs/adr/ADR-002-catalogo-json.md` — catálogo en
  `data/fuentes.json` versionado en Git, escritura atómica.
- `docs/adr/ADR-003-cli-local.md` — interfaz v1: CLI local sin
  servidor.
- `docs/adr/ADR-004-sin-red-v1.md` — la herramienta no hace red en
  la v1; el humano descarga, la herramienta registra evidencia.
- `docs/adr/ADR-005-ambito-piloto-catalogos.md` — v1 limitada a la
  sección "Catálogos para los SIS".
- `docs/adr/ADR-006-consumidor-primario-agentes.md` — consumidor
  primario: agentes de IA; salida `--json` (contrato v1.1).

Fronteras: `docs/f1-contratos.md` (registro-de-fuente v1,
cli-infosalud v1.1, máquina de estados de vigencia).
