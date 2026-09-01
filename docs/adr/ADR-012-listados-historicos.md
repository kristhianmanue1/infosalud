# ADR-012: Vigencia sobre listados históricos — tomar la última ingresada

Estado: aceptado (orientación del humano 2026-09-01: los rubros del
portal llevan lista histórica de Excels; recomienda tomar sólo la
última ingresada salvo pedido expreso)
Fecha: 2026-09-01

Contexto: los rubros principales del portal (IFU, catálogos de
unidades médicas, etc.) publican cada actualización como un archivo
NUEVO (URL nueva) en una página de listado histórico. Hoy la fuente
registra la URL de UN archivo: si el portal publica una versión
nueva en otra URL, `vigencia-verificar` seguirá descargando la vieja
y reportará `vigente` indefinidamente — falso negativo de vigencia.

Decisión:
  1. Nuevo campo opcional `url_listado` en registro-de-fuente: la
     página del portal con la lista histórica del catálogo. Añadir
     campo opcional es compatible (no exige v2).
  2. `vigencia-verificar <id>` con `url_listado`: GET de sólo lectura
     del listado, extracción de enlaces a archivos (mismo host,
     extensiones conocidas: xlsx/xls/pdf/zip/csv/doc/docx) y
     selección de la ÚLTIMA INGRESADA por heurística de fecha
     embebida en texto/URL (ISO aaaa-mm-dd, dd_mm_aaaa, ddmmaaaa,
     mes-aaaa en español); si ninguna tiene fecha, se asume que el
     listado ordena del más reciente primero (primer enlace).
  3. Si la última ingresada difiere de la URL registrada: se descarga
     y verifica la nueva, la verificación registra `url_previa`
     (campo opcional nuevo) y el registro actualiza su `url` — el
     sondeo siguiente vigila la versión nueva. La anterior no se
     borra: queda en el historial (append-only) y en url_previa.
     Versiones históricas sólo bajo pedido expreso del humano.
  4. Sin `url_listado`, el comportamiento es el actual (URL fija).
     El análisis del listado es de mejor esfuerzo: si el listado
     falla o no tiene enlaces legibles, se registra el fallo y NO se
     descarga nada (fail-closed; nunca se inventa "última versión").

Alternativas descartadas:
  - Vigilar sólo la URL fija registrada: falso `vigente` ante
    versiones nuevas en otra URL (el hueco que motiva este ADR).
  - Bajar TODO el histórico: contra la prudencia D6 (frecuencia
    contenida) y sin requisito; históricos sólo bajo pedido expreso.
  - Actualizar `url` sin registro: la mutación silenciosa del
    registro rompe trazabilidad; `url_previa` en la verificación la
    documenta (append-only).
  - Parsear fechas con lógica por-sitio frágil: heurística general
    declarada + fallback de orden del listado; los casos dudosos se
    revisan con el historial a la vista.

Consecuencias: gana detección real de "salió versión nueva" —el caso
dominante del portal— y autorreparación del registro (url apunta
siempre a la última). Pierde simplicidad: un parser de listado
(html.parser, stdlib) que mantener ante cambios de maquetación del
portal; un falso "último" queda documentado en url_previa y es
auditable. Las fuentes ya registradas conservan su URL fija hasta
que se les asigne `url_listado`.
