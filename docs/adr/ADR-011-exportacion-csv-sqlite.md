# ADR-011: Exportación de insumos a CSV y SQLite (etapa 2)

Estado: aceptado (autorización humana 2026-09-01: "adelante con
pendientes 2, 3 y 4")
Fecha: 2026-09-01

Contexto: el horizonte por etapas declarado en ADR-008 marca como
etapa 2 procesar los insumos a CSV y SQL conservando la evidencia de
origen (huella, fecha). Los archivos ya se descargan y verifican con
`vigencia-verificar`; falta el producto derivado consumible por otros
sistemas y agentes sin leer Excel.

Decisión:
  1. Comando `fuente-exportar <id> [--formato csv|sqlite]
     [--destino <directorio>]`: convierte el archivo local verificado
     de la fuente en productos derivados.
     - CSV: un archivo por hoja `<id>__<hoja>.csv` (primera fila =
       encabezados, UTF-8 con BOM) más `<id>__evidencia.json`
       (id, fecha, huella, origen).
     - SQLite: base `<id>.sqlite`, una tabla por hoja (nombre
       saneado, columnas de la primera fila, todo TEXT) y tabla
       `evidencia` (fuente, hoja, huella, fecha, filas).
  2. Origen: el archivo de la última verificación con huella; se lee
     sólo (nunca se modifica). Productos en `data/exportaciones/<id>/`
     por defecto; si el destino existe, se rechaza (sin pisar
     productos previos).
  3. Alcance de formatos: sólo tabulares (xlsx con lector de
     ADR-009/010; csv directo). PDF/ZIP quedan fuera hasta tener
     lector.
  4. La evidencia viaja por PRODUCTO (tabla/sidecar), no por fila:
     la trazabilidad del producto completo es la huella del origen;
     etiquetar cada fila multiplica el tamaño sin requisito.
  5. Producto derivado y reproducible: no participa en la máquina de
     vigencia; si la fuente cambia (`cambiada`), se re-exporta.
     stdlib-only: csv + sqlite3 (ADR-001).
  6. Topes declarados: 30 hojas, 200 columnas, 200 000 filas por
     hoja; escritura a directorio temporal y movimiento final.

Alternativas descartadas:
  - Etiquetar cada fila con huella/fecha: explosión de tamaño sin
    requisito que lo pida; el consumidor puede unir por clave si
    algún día lo necesita (contrato nuevo).
  - Emitir .sql textual: menos útil que una base SQLite lista para
    consultar; sqlite3 es stdlib y REQ-7 (intranet) lo permite.
  - Procesar PDF/ZIP en esta etapa: sin lector stdlib razonable;
    esperar requisito real.

Consecuencias: gana insumos consultables por SQL y CSV estándar para
MOCE/SIMO/analistas sin depender de Excel, con evidencia de origen
embebida. Pierde simplicidad: un producto derivado que mantener y
re-exportar tras cada `cambiada`; topes que habrá que revisar si
algún catálogo crece más allá de 200 000 filas.
