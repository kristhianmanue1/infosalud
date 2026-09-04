# Ronda adversarial de diseño — 2026-09-04

Objetivo: atacar las implementaciones de esta sesión antes de darlas
por estables: `segmentos` (multi-bloque), `conciliaciones` (grupos
de agregación), `filas_nota`, `columnas_numericas` por muestreo,
dimensiones canónicas, auditoría nivel 1 y el lote CUUMSP. Método:
contexto fresco (revisor adversarial independiente) + sondas propias
verificadas contra código y datos reales.

## Veredicto general

La frontera (validación de perfiles) es estricta, pero el runtime
**confiaba ciegamente en que el archivo coincide con lo declarado**:
cada desviación (hoja ausente, segmento desordenado, grupo fuera de
rango, huella distinta) degeneraba en silencio en lugar de
fail-closed o `requiere_revision`. Ese patrón se corrigió.

## Hallazgos y correcciones

Hallazgos corregidos en esta misma ronda:

- **H-1 (alta)**: hoja declarada en el perfil pero ausente del
  archivo → respuesta "limpia" vacía (pérdida del 100% enmascarada).
  Corregido: `construir` marca `ausente_del_archivo` +
  `requiere_revision` (test en test_servicio).
- **H-2 (alta)**: `segmentos` sin validar orden ni solapamiento →
  filas duplicadas o ventanas vacías en silencio. Corregido: el
  validador exige orden por fila_encabezados y rangos no solapados.
- **H-3 (alta)**: con `segmentos`, los campos de tabla a nivel
  hoja se aceptaban y el runtime los ignoraba en silencio.
  Corregido: el validador los rechaza.
- **H-4 (alta)**: el lote CUUMSP pisaba perfiles refinados a mano.
  Corregido: omite fuentes con perfil existente y lo reporta.
- **M-1**: `huella_base` del perfil sin cotejo en runtime →
  `/datos` expone `perfil_huella_desactualizada`.
- **M-2**: grupos de conciliación no evaluables se descartaban →
  se reportan `no_evaluado` + `reconciliado: false`.
- **M-3**: el parser numérico aceptaba `inf`/`nan`/`1_0` → regex
  estricta.
- **M-4**: dimensiones perdía atributos inexistentes en silencio →
  expone `atributos_omitidos`.
- **M-5 + L-6**: informes de auditoría se pisaban el mismo día y
  la escritura no era atómica → nombre con hora + temporal/rename.
- **L-2**: `tolerancia: 1e9` neutralizaba la conciliación → techo
  `0 < tolerancia <= 0.5` en hoja/segmento/grupo.

## Confirmados como comportamiento correcto (no bugs)

- `fuera_de_rango` acotado por bloque en multi-segmento (ventana
  hasta el encabezado del siguiente).
- Bancos de Sangre descuadrado (Σ 13.97M vs 14.56M) no es bug del
  parser: es inconsistencia real del archivo, que la conciliación
  advisory debe reportar.

## Debilitamientos conocidos (documentados, sin corregir hoy)

- Lectura topada a 200k filas ANTES de calcular `fuera_de_rango`
  (L-4): hojas mayores quedan fuera del tripwire.
- Celdas booleanas `False` cuentan como contenido (L-5).
- `huella_informe` es verificable pero nada la verifica al leer (M-5b).
- Filas totales/notas del CUUMSP dentro del rango de datos sin
  declarar (L-3) — pendiente del refinamiento por corte.
