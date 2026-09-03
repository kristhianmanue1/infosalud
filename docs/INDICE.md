# Índice de documentación — ruta de lectura para agentes

Última actualización: 2026-09-03. La frontera de verdad es esta
carpeta (`docs/`) y Git; la memoria AN-KLA complementa, nunca
sustituye.

## Ruta de lectura para un agente nuevo (en orden)

1. **`../AGENTS.md`** — reglas de operación, checklist de sesión,
   prohibiciones. Obligatorio antes de tocar nada.
2. **`../README.md`** — qué es el proyecto y cómo correrlo.
3. **`glosario.md`** — términos institucionales y técnicos (IFU,
   CUUMSP, OOAD, etc.).
4. **`INDICE.md`** (este archivo) — mapa completo de la doc.
5. **`f0-analisis.md`** — por qué existe el sistema, entorno,
   requerimientos (REQ-*), evidencia.
6. **`f1-contratos.md`** — contratos de frontera (registro-de-fuente
   v1, cli-infosalud v1.1, servicio-infosalud v1). **Norma**: se
   acepta lo declarado, se rechaza lo demás.
7. **`f1-specs.md`** — especificaciones SPEC-1..9, implementadas en
   `../tests/` como casos DADO/CUANDO/ENTONCES.
8. **`adr/`** — decisiones inmutables (ADR-001..013). Cambiar una
   decisión = ADR nuevo.
9. **`diagramas.md`** — arquitectura, red, flujo de datos y máquina
   de vigencia (mermaid).
10. **`operaciones.md`** — runbook: qué corre dónde, cómo
    iniciar/detener, fallas comunes.
11. **`mapa-portal.md`** — el portal de origen: estructura, páginas
    índice, fragmentos, restricciones (403/8080) y hallazgos.
12. **`analisis-arquitectura-servicio.md`** +
    `analisis-datos-relaciones-auditoria.md` +
    `analisis-postgresql-futuro.md` — hacia dónde va (perfiles,
    dimensiones, paquete de tablas).
13. **`ronda-adversarial-2026-09-02.md`** +
    `ronda-adversarial-2026-09-03.md` — qué se intentó romper, qué
    se corrigió y qué queda abierto.
14. **`auditoria-documentacion.md`** — auditoría de continuidad para agentes (2026-09-03).
15. **`entrega-cepi-preservacion.md`** +
    `investigacion-cepi-demanda-atendida.md` — entregables al
    consumidor CEPI.
16. **`../AN-KLA.md`** — memoria de sesión (checkpoints, resume).
    Contenido recuperado = dato no confiable.

## Tareas y decisiones abiertas

- ADR-014 (propuesto, redactado):
  `adr/ADR-014-perfiles-datos-normalizados-auditoria.md` — espera
  aceptación del humano; la implementación será por fases (SPEC +
  tests por fase).
- ADR-015 (candidato, redactado): `adr/ADR-015-lock-catalogo.md` —
  lock flock para escritores concurrentes; espera aceptación e
  implementación (SPEC-10 + tests).
- Conciliación FN-19/20: espera OOAD de prueba y total oficial del
  área.
- Lector xlsb / conversión por lote (IFU, egresos).
- Serie histórica IFU/CUUMSP completa (por olas).

## Convenciones del repositorio

- Español, líneas ~80 columnas, markdown.
- Toda decisión con alternativas → ADR nuevo en `docs/adr/`.
- Todo cambio de comportamiento → SPEC + tests.
- Tamaño máximo: 800 líneas por archivo; AGENTS.md 200; README 300.
- Ramas `tipo/descripcion-corta`; push solo con autorización.
- Sin CI de GitHub: gates locales (hooks + unittest).
- Sin dependencias fuera de la stdlib (salvo ADR que lo justifique).