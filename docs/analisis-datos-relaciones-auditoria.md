# Análisis: JSON suficiente, relaciones entre fuentes,
# contaminación de totales y auditoría por agente (2026-09-03)

Responde cuatro preguntas sobre el nivel 2 (datos normalizados,
docs/analisis-arquitectura-servicio.md §3) antes de implementarlo.

## A. ¿El JSON actual es suficiente?

**No — y eso es correcto a esta altura.** El envelope actual
(`/archivo/meta`) es un contrato de **archivo** (procedencia e
integridad), no de **contenido**. Sirve para auditar y descargar,
no para consultar. Lo que falta es el contrato de **hoja**:

```json
{
  "id": "poblacion-pamf-siais-2025",
  "sha256": "6e4a3b95…",
  "hojas": [
    {"nombre": "PAMF_202506_UM_Totales",
     "tipo": "datos",
     "fila_encabezados": 4,
     "columnas": ["clave_um", "nombre_um", "pamf"],
     "filas_datos": {"desde": 5, "hasta": 1742},
     "clave_primaria": "clave_um"}
  ]
}
```

Este "perfil estructural" por hoja es el que evita el problema (C):
decir explícitamente dónde están los encabezados, dónde empiezan y
terminan los datos, y qué filas son totales. La herramienta actual
(`estructura.leer_filas`, ADR-010 borrador) ya detecta encabezados
en cualquier fila y descarta hojas descriptivas — el perfil formaliza
ese criterio y lo **persiste versionado** (`data/perfiles/<id>.json`),
de modo que la normalización no dependa de heurísticas re-ejecutadas.

## B. Relaciones entre fuentes

**Las relaciones no se inventan: se resuelven por claves contra
dimensiones canónicas.** Los catálogos ya capturados SON las tablas
de dimensión:

| Dimensión | Fuente canónica | La usan |
|---|---|---|
| Unidad médica | `catalogo-ooad-subdelegaciones` + CUUMSP | todos los datos por unidad |
| OOAD/subdelegación | mismo catálogo | agregación OOAD (FN-19) |
| Servicio/especialidad | `catalogo-servicios-especialidades-maestro` + conversor SIMO/MOCE | productividad por servicio |
| Periodo | `catalogo-maestro-semanas-estadisticas` | cierres semana/mes/año |

Propuestas:

1. **Dimensiones como endpoints de primera clase**:
   `GET /dimensiones/unidad`, `/dimensiones/servicio` — JSON de
   clave→atributos, derivado del catálogo verificado (con huella).
2. **Cada dataset normalizado declara sus claves** (`clave_primaria`,
   `claves_foraneas: {unidad: "dimensiones/unidad"}`) en su perfil.
3. **Métrica de calidad obligatoria**: *cobertura de clave* = % de
   filas cuya clave resuelve contra la dimensión. Un join con
   cobertura < 100% no es error, pero se reporta visible
   (`{resueltas: 1732, sin_resolver: 17, ejemplo: "UM-0423"}`).
4. Regla: una relación entre dos fuentes solo existe si **ambas
   declaran la misma dimensión** — así FN-19 (casos de una fuente ÷
   PAMF de otra) es un join por `clave_um` auditado, no una
   coincidencia de nombres de columna.

## C. Totales en primeras filas y mezcla de contenido

**El riesgo real y cómo se contiene.** Los archivos del portal
mezclan tres tipos de contenido: portadas/títulos, encabezados en
fila arbitraria, y filas de totales (p. ej. "Egresos por OOAD y
UMAE… 2024" trae encabezado compuesto; Cifras Nacionales intercala
totales). Mezclarlos infla sumas — exactamente lo que arruinaría
FN-19/20.

Defensas, en orden:

1. **Perfil por hoja** (punto A): `tipo` de hoja y rango de filas
   de datos explícitos. Lo que está fuera del rango **no entra** al
   JSON de datos — los totales no se "detectan" al vuelo: se
   declararon al crear el perfil.
2. **Separación, no eliminación**: las filas de totales detectadas
   se sirven aparte (`"segmentos": {"datos": […], "totales": […]}`)
   — conciliar totales declarados contra suma de detalles es una
   **prueba de calidad**, no basura.
3. **Reconciliación automática**: si el perfil declara `fila_total`,
   el servicio verifica `Σ(detalles) ≈ total` (con tolerancia) y
   reporta `reconciliado: true/false`. Es la misma lógica de la
   conciliación FN-19/20 aplicada dentro del archivo.
4. Caso PAMF: ya viene limpio por diseño (hojas separadas
   `UM_Totales` / `OOAD` / `Consultorios`) — el perfil solo lo
   declara. Caso Cifras Nacionales: requerirá perfil con rango.

## D. Auditoría de estructura y lógica por agente de IA

**Sí, y en dos niveles con disparadores distintos** (no siempre
todo: la auditoría completa es cara).

| Nivel | Disparador | Qué hace el agente | Veredicto |
|---|---|---|---|
| **1. Diff estructural** (automático, cada cambio) | `vigencia-verificar` detecta huella nueva | diff contra el perfil vigente: hojas nuevas/eliminadas, columnas renombradas/agregadas, filas de menos | conforme (diff trivial) / **requiere revisión** (cambió estructura) |
| **2. Auditoría lógica** (agente IA, programada — p. ej. mensual — o bajo demanda) | calendario o disparo manual, y siempre tras un nivel 1 adverso | consume `/datos` + perfiles + dimensiones: reconciliación de totales, cobertura de claves, cambios de lógica (unidades de medida, cortes), comparación contra total oficial del área | informe de auditoría |

Artefactos y gobernanza:

- El informe de auditoría es un **artefacto versionado**
  (`data/auditorias/<id>/<fecha>.json`): veredicto
  {conforme | observado | rechazado}, hallazgos, huella auditada
  y qué agente/modelo lo produjo — nunca sobrescribe el dato,
  solo lo califica.
- Mientras una fuente esté `rechazada`, el servicio lo declara en
  `/archivo/meta` (`estado_semantico: "rechazada_por_auditoria"`)
  — conecta con el campo que ya existe en el envelope.
- La memoria (AN-KLA) guarda las **lecciones** de cada hallazgo,
  no los informes completos (frontera de verdad: docs/ y Git son
  canónicos).

Correcciones por ronda adversarial de diseño (2026-09-03,
docs/ronda-adversarial-2026-09-03.md):

- **Veredicto advisory**: el agente solo puede marcar
  `requiere_revision`; `rechazada` exige confirmación del área/humano.
  El informe registra modelo, versión y fecha (no determinista).
- **Perfil desactualizado = pérdida silenciosa**: tras normalizar se
  expone `fuera_de_rango: n` (filas con contenido fuera del rango
  declarado); n > 0 → `requiere_revision` (disparador del nivel 1).
- **Parser numérico + tolerancia explícita** para la reconciliación
  ("1,234.56", subtotales intercalados, múltiples filas de total).
- **Dimensiones**: tabla de alias por sistema y **ciclo propio de
  vigencia** con fecha de corte visible (el catálogo OOAD vence).

## E. Requisitos para implementar (cuando se apruebe)

1. ADR-014: perfiles estructurales + niveles de datos + auditoría.
2. Esquema de perfil v1 + tests DADO/CUANDO/ENTONCES (totales fuera
   de rango, encabezado en fila 4, clave sin cobertura).
3. Perfiles iniciales: los 6 archivos del piloto CEPI (el agente
   los genera con el borrador asistido como base y los valida).
4. Endpoint `/datos` con ETag = huella (sinergia de caching ya
   analizada en el documento de arquitectura §4).
5. Endpoints `/dimensiones/*` servidos desde los catálogos.