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
| 2021 | 11 de 12 | sin MAYO; ENERO con sufijo `_n` |
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

## Perfiles por lote de los cortes CUUMSP (2026-09-04)

`scripts/generar_perfiles_cuumsp_lote.py`: los 67 cortes CUUMSP
xlsx (2021–2026, incluidos los 14 de las brechas) perfilados por
lote: hoja 'Unidad Médica' con encabezado localizado dinámicamente
(fila 10; fila 13 en 2021 que intercala notas), clave
`CLUES  Salud`, 37-40 columnas; hojas no tabulares declaradas
descriptivas. Correcciones incluidas: `fuera_de_rango` ignora
celdas de sólo espacios (artefacto real en dic-2021 f1472) y la
búsqueda de encabezado exige celda que INICIE con 'CLUES' (la nota
de 2021 menciona CLUES dentro de una URL). Verificado en vivo:
`perfil_aplicado: true`, `fuera_de_rango: 0` en cortes de cada año.
Total de perfiles en `data/perfiles/`: 75.

### Serie CUUMSP cerrada

Con las brechas localizadas en el fragmento `seccion/6` (páginas
`cuumsp2021n`, `cuumsp202312`, `cuumsp202401n`), la serie 2021–2026
quedó completa: 12 cortes por año (2021: 12, 2022: 12, 2023: 12,
2024: 12, 2025: 13, 2026: 8+agosto) + páginas índice registradas
(`recursos-cuumsp-2021n/2022/202312/202401n/2025/2026`). Sólo
`recursos-cuumsp-mayo-2023` permanece `inaccesible` (el archivo no
existe en el portal en ninguna variante de nombre). Además, el
fragmento revela páginas para 2012–2020: material de olas futuras.

## columnas_numericas activadas (2026-09-04, v2)

Perfiles de cifras-nacionales y productividad semanal a v2 con
`columnas_numericas` por muestreo (>= 80% parseable) y columnas
renombradas desde la fila sub (los nombres de métrica). Scripts:
`scripts/activar_numericas_cifras.py` y
`scripts/activar_numericas_productividad.py`.

Resultados de la conciliación en vivo:
- productividad (Resumen): **reconciliado True — 24/24 columnas
  exactas** (Σ delegaciones = Total Nacional, ±0.5%).
- cifras PAMF Mes: **reconciliado True — 21/21**.
- cifras Consultas y Mortalidad: `reconciliado False` — honesto y
  valioso: Σ(filas) mezcla delegaciones + UMAE + categorías fuera
  de IMSS, que no suma contra el total declarado. La conciliación
  advisory revela que falta declarar la semántica de agregación de
  filas (qué filas suman a qué total) — insumo directo para la
  fase de dimensiones, no un bug del parser.

## Conciliaciones por grupo extendidas a cifras (2026-09-04, v4)

Todos los grupos verificados aritméticamente antes de declararse
(enmienda `conciliaciones`): Delegaciones / UMAE / Nacional por
hoja. Resultados en `/datos`:

| Hoja | Resultado |
|---|---|
| Consultas, Aux Dx, Aux Tx, 33 Procedimientos, Atenciones Prof., Egresos | `reconciliado: True` (3 grupos exactos) |
| PAMF Mes | `reconciliado: True` (21/21 por filas_total) |
| Mortalidad | `reconciliado: True` (Nacional acotado a col. `Total`: las categorías por edad no tienen desglose fuera de IMSS) |
| Banco de Sangre | `reconciliado: False` — hallazgo real: `TOTAL DE MILILITROS TRANSFUNDIDOS` (Σ 13.97M vs 14.56M declarado) y `TOTAL DE TRANSFUSIONES` (62,875 vs 65,624) no cuadran contra Σ de las filas del rango; los bancos declarados no explican el total nacional. Observado para revisión semántica del área (la conciliación advisory califica, no bloquea). |

## Fase 3 implementada: conciliación numérica

`/datos` incluye ahora el bloque `conciliacion` por hoja cuando el
perfil declara `columnas_numericas` + `filas_total`: parser
numérico tolerante (comas de millar, $, %), Σ(detalles) contra
cada total con la tolerancia declarada (defecto ±0.5%),
`reconciliado: true/false` con ejemplos de descuadre (hasta 3) —
sin bloquear el dato: lo califica. (Corrección adversarial #5.)

## Enmienda segmentos implementada (2026-09-04)

`segmentos: [{nombre, fila_encabezados, [fila_encabezados_sub],
columnas, filas_datos, [clave_primaria], [filas_total],
[columnas_numericas], [tolerancia]}]` por hoja (>= 2 segmentos):
declara las tablas independientes de una hoja multi-bloque. En
`/datos` cada segmento se expone con su nombre y su
`fuera_de_rango` acotado a su bloque (termina donde inicia el
encabezado del siguiente segmento). Reglas: los campos de tabla se
declaran dentro de cada segmento (no en la hoja), nombres únicos y
totales fuera del rango de su segmento. Implementado en
`perfiles.py` (validador) y `datos.py` (`segmentar` → `_tabla`).
Nota: el hallazgo posterior mostró que productividad semanal tiene
una tabla por hoja y se perfiló con el contrato base; `segmentos`
queda disponible para hojas verdaderamente multi-bloque.

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