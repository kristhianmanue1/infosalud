# Uso de Skevi en este proyecto

**Proyecto:** Infosalud Nexus
**Fase actual:** F2 (cascarón) — F0 y F1 cerradas
**Fuente del método:** clon local `skevi/` de
github.com/kristhianmanue1/skevi (commit de clonado: 2026-09-01)

## Qué leer primero

1. `AGENTS.md` en la raíz — punto de entrada, trae el bloque de
   registro que enlaza a este archivo.
2. `skevi/docs/ai-agent-guide/00-INDICE.md` — fases F0→F3 y reglas
   de aplicación.
3. `skevi/docs/estandar-diseno-software-github.md` — capa normativa
   transversal.

## Desviaciones de este proyecto respecto al estándar por defecto

Ninguna: hereda los límites por defecto (800/200/300 líneas). La
guía vive como clon anidado ignorado por Git (`skevi/`, ver
README §"Sobre skevi/"), no copiada a `docs/`.

## Verificación local

```bash
python3 -m compileall -q infosalud && python3 -m unittest discover -s tests
```

## Dónde están los ADRs y specs de F1

- ADRs: `docs/adr/` (ADR-001…006)
- Specs: `docs/f1-specs.md`
- Contratos y máquina de estados: `docs/f1-contratos.md`
- Análisis F0 y decisiones D1-D5: `docs/f0-analisis.md`
