# Auditoría de documentación para continuidad de agentes IA
# (2026-09-03)

Pregunta: ¿la documentación del proyecto es suficiente, según las
mejores prácticas de arquitectura, desarrollo y administración de
proyectos, para que agentes de IA continúen el trabajo? Veredicto
con evidencia: **sí en lo esencial, con 4 huecos cerrados en esta
misma auditoría** (ver §3).

## 1. Inventario verificado (3,390 líneas + tests + 13 ADRs)

- Punto de entrada agent-native: `AGENTS.md` (checklist de sesión,
  reglas, prohibiciones).
- Memoria de continuidad: AN-KLA (checkpoints, resume, lecciones).
- Análisis: F0, arquitectura del servicio, datos/relaciones/
  auditoría, PostgreSQL futuro, investigación CEPI, entrega CEPI.
- Contratos versionados: `f1-contratos.md` (registro-de-fuente v1,
  cli-infosalud v1.1, servicio-infosalud v1) con enmiendas datadas.
- Especificaciones ejecutables: `f1-specs.md` (SPEC-1..9) → 10
  archivos de tests con casos DADO/CUANDO/ENTONCES.
- Decisiones: 13 ADRs inmutables (método skevi).
- Mapas del dominio: `mapa-portal.md`, `despliegue-halt-to-safe.md`.
- Operación: `sondeo-launchd.md`, `deploy/routes-cloudflare.sh`,
  plists, `Dockerfile`/`docker-compose.yml`.
- Datos: `data/fuentes.json` (70 fuentes, esquema cerrado),
  20+ diccionarios, conversor, entregas.

## 2. Evaluación por dimensión (mejores prácticas)

| Dimensión | Veredicto | Evidencia |
|---|---|---|
| Entrada para agentes | ✅ | AGENTS.md + ADR-006 |
| Continuidad entre sesiones | ✅ | AN-KLA checkpoint/resume |
| Contratos de frontera | ✅ | f1-contratos v1.1 + v1 del servicio |
| Especificación ejecutable | ✅ | SPECs → tests DADO/CUANDO/ENTONCES |
| Decisiones (ADRs) | ✅ | 13 ADRs, inmutables, método skevi |
| Mapa del dominio externo | ✅ | mapa-portal + despliegue |
| Análisis crítico | ✅ | 4 rondas adversariales documentadas |
| **Índice de documentación** | ❌→✅ | no existía; creado: `docs/INDICE.md` |
| **Diagramas consolidados** | ❌→✅ | ASCII disperso; creados: `docs/diagramas.md` |
| **Runbook de operaciones** | ❌→✅ | repartido; consolidado: `docs/operaciones.md` |
| **Glosario institucional** | ❌→✅ | términos dispersos; creado: `docs/glosario.md` |

## 3. Huecos cerrados (archivos nuevos de esta auditoría)

1. `docs/INDICE.md` — mapa de toda la documentación con ruta de
   lectura para un agente nuevo (qué leer, en qué orden, para qué).
2. `docs/diagramas.md` — arquitectura, topología de red, flujo de
   datos y máquina de vigencia en mermaid (renderizable en GitHub).
3. `docs/operaciones.md` — runbook: qué corre dónde, cómo
   iniciar/detener cada pieza, fallas comunes y su solución
   (Fortinet, deriva de IPs, carrera de escritores, xlsb).
4. `docs/glosario.md` — términos institucionales (IFU, CUUMSP,
   OOAD, UMAE, PAMF, CLUES, SIAIS, SIMO, MOCE) y técnicos del
   sistema.

## 4. Lo que sigue abierto (honesto)

- Perfiles estructurales y `/datos`: requieren ADR-014 (propuesto,
  especificación endurecida por adversariales).
- Lock de catálogo: ADR-015 implementado (SPEC-10, lock flock en
  los tres escritores de la CLI).
- Conciliación FN-19/20: espera OOAD de prueba + total oficial del
  área (fuera del control del agente).
- Serie histórica IFU/CUUMSP completa: por olas.
- La memoria AN-KLA es complemento, no sustituto: los documentos de
  `docs/` son la frontera de verdad.

## 5. Veredicto final

Con los 4 archivos nuevos, el proyecto cumple las mejores prácticas
de documentación para continuidad por agentes: entrada agent-native,
memoria persistente, contratos versionados, especificación
ejecutable, decisiones inmutables, operación documentada, mapa del
dominio y glosario. Un agente nuevo puede reconstruir el estado
completo leyendo `docs/INDICE.md` en orden.