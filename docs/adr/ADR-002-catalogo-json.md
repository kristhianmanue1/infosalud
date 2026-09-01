# ADR-002: Catálogo persistido en JSON versionado en Git

Estado: aceptado (implementación no iniciada)
Fecha: 2026-09-01

Contexto: REQ-1 y REQ-3 exigen persistir el catálogo de fuentes y su
historial de verificaciones (SPEC-1, SPEC-2). La escala de la v1 es
una sección piloto (ADR-005): decenas de registros.

Decisión: el catálogo vive en `data/fuentes.json`, un documento JSON
con esquema cerrado (`CONTRATO: registro-de-fuente v1`), versionado
en Git y escrito atómicamente (temporal + rename).

Alternativas descartadas:
  - SQLite (está en la stdlib): consultas más ricas, pero archivo
    binario no diffable: el historial de Git dejaría de auditar los
    cambios de contenido, que es justamente el valor central
    (REQ-3, REQ-8).
  - CSV: esquema cerrado frágil ante campos anidados (la lista
    `verificaciones` no cabe sin convenciones ad hoc).

Consecuencias: gana auditoría total vía historial Git y reversibilidad
inmediata (`git revert`). Pierde rendimiento de consulta a gran
escala: aceptable para decenas/cientos de registros; si el catálogo
creciera a miles con búsquedas complejas, un ADR nuevo migraría a
SQLite conservando el contrato. Queda obligada la escritura atómica
en toda modificación (SPEC-3).
