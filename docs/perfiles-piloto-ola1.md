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

## Ola 2 CUUMSP 2021–2024 (2026-09-04)

Sondeo sistemático de URLs (los años 2021/2023/2024 no tienen
página índice en `paginas/cuumspYYYY.html`; sólo 2022). Resultado:
**33 cortes nuevos + índice 2022**, todos `vigente`
(catálogo 84→119 fuentes; 119 ids únicos, 0 huellas compartidas).

| Año | Cortes | Nota |
|---|---|---|
| 2021 | 11 de 12 | sin MAYO (no existe en ninguna variante de nombre; ENERO con sufijo `_n`) |
| 2022 | 12 de 12 | página índice sí existe; MARZO con sufijo `_n` |
| 2023 | 10 de 12 | sin ENERO ni FEBRERO |
| 2024 | 1 (AGOSTO) | los demás meses con nombres fechados no adivinables |

Brechas pendientes de localización (MAYO-2021; ENERO/FEBRERO-2023;
11 meses de 2024): requieren la página o fragmento del portal que
los enliste (el fragmento `seccion/6` por puerto 80 no respondió
en esta sesión) o confirmación de la DIS. `recursos-cuumsp-mayo-2023`
quedó registrado con verificación `inaccesible` (404) como
evidencia del intento.

## Pendientes de perfil (con causa)

- `estadisticas-nacionales-cifras-2025`: **perfilado** (10 hojas,
  `fila_encabezados_sub` para el encabezado compuesto, totales
  Nacional/Total Delegaciones/Total OOAD en `filas_total`, fila
  '**' en `filas_nota`). Pendiente opcional: declarar
  `columnas_numericas` por hoja para activar la conciliación
  automática (fase 3, ya implementada en `/datos`).
- `seguimiento-productividad-semanal-2025`: multi-bloque (varias
  tablas por hoja, notas intercaladas). Propuesta de diseño:
  `segmentos` por hoja (ver abajo); requiere enmienda + SPEC.

## Fase 3 implementada: conciliación numérica

`/datos` incluye ahora el bloque `conciliacion` por hoja cuando el
perfil declara `columnas_numericas` + `filas_total`: parser
numérico tolerante (comas de millar, $, %), Σ(detalles) contra
cada total con la tolerancia declarada (defecto ±0.5%),
`reconciliado: true/false` con ejemplos de descuadre (hasta 3) —
sin bloquear el dato: lo califica. (Corrección adversarial #5.)

## Diseño pendiente: hojas multi-bloque

Las hojas multi-bloque (varias tablas con encabezados propios en
una misma hoja, p. ej. `seguimiento-productividad-semanal-2025`)
no se resuelven con un solo `filas_datos` por hoja. Propuesta de
diseño (enmienda compatible futura): segmentos declarados —
`segmentos: [{nombre, fila_encabezados, filas_datos, ...}]` por
hoja, donde cada segmento es una tabla independiente; la respuesta
de `/datos` expondría `hojas/{nombre}/segmentos/{nombre}`. Requiere
enmienda del contrato + SPEC antes de implementar; el perfil
actual (un rango por hoja) sigue siendo válido para hojas de tabla
única.

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