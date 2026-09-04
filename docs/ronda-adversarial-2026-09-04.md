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

| # | Severidad | Hallazgo | Corrección |
|---|---|---|---|
| H-1 | ALTA | Hoja declarada en el perfil pero ausente del archivo → respuesta "limpia" vacía (pérdida del 100% del dato enmascarada) | `construir` marca `ausente_del_archivo: true` + `requiere_revision: true` (test en test_servicio) |
| H-2 | ALTA | `segmentos` sin validar orden ni solapamiento → filas duplicadas o ventanas de fuera_de_rango vacías en silencio | `_validar_segmentos` exige orden por fila_encabezados y rangos no solapados (test) |
| H-3 | ALTA | Con `segmentos`, `conciliaciones`/`filas_total`/`filas_nota`/`tolerancia` a nivel hoja se aceptaban y el runtime los ignoraba en silencio | El validador los rechaza (test por cada campo) |
| H-4 | ALTA | El lote CUUMSP pisa perfiles refinados a mano (v2+) con v1 sin aviso | El lote omite fuentes con perfil existente y lo reporta |
| M-1 | MEDIA | `huella_base` del perfil sin cotejo en runtime | `/datos` expone `perfil_huella_desactualizada: true` |
| M-2 | MEDIA | Grupos de conciliación no evaluables se descartaban en silencio | Se reportan `no_evaluado: true` + `reconciliado: false` |
| M-3 | MEDIA | Parser numérico aceptaba `inf`, `nan`, `1_0` (float de Python) | Regex estricta `-?\d+(\.\d+)?` |
| M-4 | MEDIA | Dimensiones: atributos inexistentes se perdían en silencio | La respuesta expone `atributos_omitidos` |
| M-5 | MEDIA | Auditoría: dos informes el mismo día se pisaban | Nombre con hora + escritura atómica (L-6) |
| L-2 | BAJA | `tolerancia: 1e9` neutralizaba la conciliación advisory | Techo `0 < tolerancia <= 0.5` en hoja/segmento/grupo |
| L-1, L-3..L-6 | BAJA | Duplicados en diff, techo de 200k filas, booleanos, etc. | Documentados; corrección diferida (ver Debilitamientos conocidos) |

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
