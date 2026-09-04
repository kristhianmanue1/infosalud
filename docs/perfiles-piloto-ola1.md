# Perfiles estructurales — ola 1 del piloto CEPI (informe)

Fecha: 2026-09-04 (act. 2026-09-04, ola CUUMSP + derivado 1N).
Alcance: los 6 archivos registrados con el hallazgo del puerto 80
(catálogo 23→29, 2026-09-02), que son la base del piloto CEPI
(P11, ADR-014); más la ola 1 CUUMSP 2025.

## Resultado: 4 perfiles v1 en producción

- `poblacion-pamf-siais-2025` — 4 hojas (Consultorios, UM_Totales,
  OOAD, No_Consideradas). En `/datos`: aplicado, `fuera_de_rango: 0`.
- `poblacion-consultorios-medfam-pamf-2025` — 4 hojas
  (Tot_Cons_MedFam, Tot_Cons_MF_OOAD, PAMF_Consultorios,
  NO CONTEMPLADAS). Ídem.
- `poblacion-usuaria-23n-simoc-unidad-2025` — 2 hojas (Esp, Urg;
  fila 12 = total nacional declarada en `filas_total`). Ídem;
  totales servidos aparte.
- `poblacion-usuaria-1n-unidad-2004-2025-convertido` — 22 hojas
  (una por año 2004-2025; total nacional por hoja en
  `filas_total`). Fuente derivada: conversión LibreOffice headless
  del xls original (el original manda). Ídem.

Generación semi-automática (P11): `scripts/generar_perfiles_piloto.py`
y `scripts/generar_perfil_usuaria_1n.py` extraen las columnas de la
fila de encabezados declarada, validan con el contrato
`perfil-de-fuente v1` (SPEC-11) y escriben
`data/perfiles/<id>.json` (versionado en git, P12). Verificación en
vivo contra el contenedor `1nf0541ud`: `perfil_aplicado: true`,
totales aparte y `fuera_de_rango: 0` en las 32 hojas.

## Ola 1 CUUMSP 2025 (misma sesión)

Página índice `recursos-cuumsp-2025` + 11 cortes mensuales
(enero–noviembre) registrados, descargados y `vigente`
(catálogo 70→83 fuentes, 0 ids duplicados, 0 huellas compartidas).

## Pendientes de perfil (con causa)

- `estadisticas-nacionales-cifras-2025`: encabezados compuestos de
  dos filas — resuelto a nivel contrato con la enmienda
  `fila_encabezados_sub` (2026-09-04); falta perfilar sus 10 hojas
  (layouts propios por hoja).
- `seguimiento-productividad-semanal-2025`: multi-bloque (varias
  tablas por hoja, notas intercaladas). Requiere diseño antes de
  declarar rangos.

## Hallazgos del perfilado

- Los archivos SIAIS traen portada/títulos (filas 1-7) y
  encabezados en fila 7-12 según el archivo — exactamente lo que
  el perfil formaliza; sin él, la lectura cruda mezcla portada
  con datos.
- Subtotales embebidos dentro del rango de datos (PAMF:
  `Consultorio=9999/Turno=99` por unidad; usuaria 1N: subtotales
  por unidad y filas Total Delegacional): declarados en `notas`
  del perfil; la conciliación automática (parser numérico +
  tolerancia, corrección adversarial #5) es fase 3.
- `fuera_de_rango` sólo cuenta contenido DESPUÉS del rango
  declarado: los títulos/encabezados previos son estructura
  legítima, no pérdida silenciosa.