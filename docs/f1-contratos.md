# F1 — Contratos de frontera y modelo de estados

> Fronteras del sistema según `skevi/docs/ai-agent-guide/02` §4-§5.
> Contratos cerrados: se acepta lo declarado, se rechaza lo demás.

## CONTRATO: registro-de-fuente v1

Esquema del registro de catálogo (archivo `data/fuentes.json`).

Entrada (campos cerrados):
  id: string [obligatorio] [patrón ^[a-z0-9-]+$] — identificador único
  seccion: string [obligatorio] [enum: catálogos, estadísticas-
       nacionales, censos, consulta-externa, hospital, defunciones,
       recursos, población, documentos-normativos, sitios-interés,
       seguimiento, capacitación, oficios-circulares, validación-
       información (enmienda 2026-09-01, ADR-012: mapa completo del
       portal)] — sección Infosalud; la lista crece por versión del
       contrato
  titulo: string [obligatorio] [1..200 chars] — nombre de la fuente
  url: string [obligatorio] [host *.imss.gob.mx con o sin puerto
       (enmienda 2026-09-01: el portal usa :8080), esquema http o
       https] — ubicación original
  url_listado: string [opcional, ADR-012] [mismo host/esquema que
       url] — página del listado histórico del catálogo; cuando
       existe, vigencia-verificar verifica la última ingresada del
       listado y actualiza `url` si cambió (queda `url_previa` en la
       verificación)
  parent_source_id: string [opcional, enmienda 2026-09-03, retro
       CEPI] [patrón ^[a-z0-9-]+$] — id de la fuente madre cuando el
       archivo fue descubierto desde una página índice; el alta
       rechaza referencias colgantes (el parent debe existir en el
       catálogo)
  aliases: lista de strings [opcional, enmienda 2026-09-03] [1-20
       textos de 1-100 caracteres] — alias generales de búsqueda
       (ej. "IFU", "Infraestructura Física Usada"); los usan
       fuente-buscar y la API/MCP
  corte_declarado: string [opcional, enmienda 2026-09-03] [1-100
       caracteres] — periodo o corte que el archivo declara cubrir,
       tal como aparece en su origen; NO implica vigencia
  formato: enum [obligatorio]: xlsx | xls | csv | pdf | html | otro
  periodicidad: enum [opcional]: diaria | semanal | mensual |
       anual | eventual | desconocida (ausente = desconocida)
  notas: string [opcional] [máx 500 chars] — contexto humano
  verificaciones: lista [obligatorio, inicia vacía] de:
    fecha: ISO-8601 [obligatorio] — fecha de la verificación
    resultado: enum [obligatorio]: vigente | cambiada | inaccesible
    huella: string [opcional] [sha256 hex] — del archivo presentado
    ruta_local: string [opcional] — copia local referenciada
    causa: string [opcional] [máx 200 chars] — motivo del fallo;
      presente cuando resultado = inaccesible (enmienda 2026-09-01,
      ronda adversarial F3)
    estructura: lista [opcional, ADR-009] de {hoja: string,
      columnas: lista de string} — hojas y encabezados observados en
      el archivo verificado (sólo xlsx, extracción de mejor esfuerzo:
      primera fila, topes 30 hojas / 200 columnas)
    estructura_causa: string [opcional] [máx 200 chars] — motivo por
      el que no se extrajo estructura; un fallo de extracción nunca
      altera `resultado` (ADR-009)
    url_previa: string [opcional] [máx 300 chars] — URL registrada
      antes de la verificación, cuando el listado histórico reveló
      una versión más nueva y `url` del registro se actualizó
      (ADR-012; trazabilidad append-only)

Salida: el registro almacenado, idéntico al validado.
Errores:
  E-VALID: campo faltante, fuera de rango o no declarado → rechazo;
    el catálogo queda sin cambios.
  E-DUPLICADO: id ya existente → rechazo; catálogo sin cambios.
Invariantes:
  - id único; url dentro de *.imss.gob.mx.
  - Ningún campo fuera del esquema; ningún payload opaco.
  - Toda verificación lleva fecha (trazabilidad, REQ-8).
Compatibilidad: añadir valores a enums o campos opcionales es
  compatible; quitar campos, cambiar tipos o estrechar rangos exige
  v2 y migración registrada.

## CONTRATO: diccionario-de-fuente v1 (ADR-009)

Archivo por fuente: `data/diccionarios/<id>.json` (junto al
catálogo). Describe el contenido declarado de una fuente: qué
campos tiene, qué significan y cómo se usa. Es documentación
esquematizada, no evidencia; la estructura observada por
verificación vive en `registro-de-fuente` (campo `estructura`).

Entrada (campos cerrados):
  id: string [obligatorio] [patrón ^[a-z0-9-]+$] — debe existir en
       el catálogo y coincidir con el nombre del archivo
  descripcion: string [opcional] [1..1000 chars] — qué contiene la
       fuente y para qué sirve
  uso: string [opcional] [máx 500 chars] — mecanismo de uso: cómo
       se interpreta, con qué se cruza, qué campo es la clave
  huella_base: string [opcional] [sha256 hex] — huella del archivo
       contra el que se levantó el diccionario (procedencia)
  fecha: ISO-8601 [opcional] — fecha del levantamiento
  campos: lista [obligatorio, ≥1] de:
    nombre: string [obligatorio] [1..100 chars]
    tipo: enum [obligatorio]: texto | numero | fecha | clave |
          booleano | otro
    descripcion: string [opcional] [máx 300 chars]
    obligatorio: booleano [opcional] (ausente = falso)
    valores: string [opcional] [máx 200 chars] — dominio o valores
          observados
    ejemplo: string [opcional] [máx 200 chars]
  metadatos: lista [opcional, ADR-010] de:
    hoja: string [obligatorio] — nombre de la hoja descriptiva
    metadatos: lista [obligatorio] de {etiqueta: string [≤100],
      contenido: string [≤500]} — líneas etiqueta→contenido leídas
      de esa hoja (fuente publicada; no inferida)

Salida: el archivo almacenado, idéntico al validado (escritura
  atómica temporal + rename).
Errores:
  E-VALID: campo faltante, fuera de rango, tipo fuera del enum o
    campo no declarado → rechazo; archivo sin cambios.
  E-NOEXISTE: id inexistente en el catálogo, o consulta de
    diccionario inexistente.
Invariantes:
  - Ningún campo fuera del esquema; id del archivo = id solicitado
    = id de la fuente en el catálogo.
  - El diccionario no altera la máquina de estados de vigencia.
Compatibilidad: añadir campos opcionales o valores de enum es
  compatible; lo demás exige v2.

## CONTRATO: cli-infosalud v1.1

Interfaz v1 (frontera CLI, sin red). v1.1 (2026-09-01, ADR-006):
consumidor primario = agentes de IA; se añade `--json` a todos los
comandos. Sin consumidores externos aún, el salto v1→v1.1 se
registra aquí antes de la primera implementación.

Entrada:
  Todos los comandos aceptan `--json` [opcional]: salida JSON
  parseable en stdout (un objeto por ejecución, incluidos los
  fallos — objeto con clave "error"—); diagnóstico en stderr.
  Sin `--json`, salida en texto plano para el humano.
  Uso inválido de argumentos sale con código 1, no 2 (el código 2
  queda reservado para E-NOEXISTE). En fuente-buscar, el término
  vacío se rechaza como E-VALID (salida 1).
  [Enmiendas 2026-09-01, ronda adversarial F3; sin consumidores
  externos aún.]
  fuente-alta --archivo <ruta>: da de alta un registro JSON válido
    [obligatorio: ruta a archivo conforme a registro-de-fuente v1]
  fuente-lista [--seccion <s>] [--formato <f>]: lista registros
  fuente-buscar <termino>: búsqueda por término en id/titulo/notas
  fuente-detalle <id>: muestra el registro completo, incluida la
    URL original y la ruta local si existe
  fuente-campos <id> [--archivo <ruta>] [--borrador]: muestra
    (texto o --json) o crea/actualiza (con --archivo validado,
    ADR-009) el diccionario de datos de la fuente; consulta sin
    diccionario → salida 2. Con --borrador (ADR-010): enriquece el
    diccionario con evidencia observada del archivo local verificado
    (valores, ejemplos y metadatos de hojas descriptivas); nunca
    genera ni sobrescribe descripciones; --archivo y --borrador son
    mutuamente excluyentes
  fuente-exportar <id> [--formato csv|sqlite] [--destino <dir>]:
    exporta el archivo local verificado a productos derivados con
    evidencia de origen (ADR-011): CSV un archivo por hoja más
    `<id>__evidencia.json`, o base SQLite `<id>.sqlite` con una
    tabla por hoja y tabla `evidencia`; destino por defecto
    `data/exportaciones/<id>/<formato>`; destino existente →
    salida 1
  vigencia-registrar <id> --archivo <ruta>: registra verificación
    comparando la huella sha256 del archivo presentado con la previa
  vigencia-verificar <id> [--destino <ruta>]: descarga la fuente de
    su URL registrada (GET de sólo lectura, ADR-008) a destino —por
    defecto data/descargas/<id>/<archivo>— y registra la verificación
    con su evidencia (fecha, huella sha256, ruta local). Salvaguardas
    fail-closed: timeout explícito, tamaño máximo, verificación
    mínima de contenido (rechaza p. ej. HTML 200 para un xlsx), sin
    redirects fuera del host original, descarga temporal + rename.
    Si la fuente tiene `url_listado` (ADR-012), verifica la última
    ingresada del listado; si difiere de la URL registrada, actualiza
    `url` y registra `url_previa` (históricos sólo bajo pedido
    expreso)
  vigencia-historia <id>: lista el historial cronológico

Salida: texto plano; código 0 en éxito.
Errores:
  1: E-VALID o E-DUPLICADO, o fallo de entorno (catálogo ausente o
     corrupto; fallo de red o de contenido en vigencia-verificar,
     que registra `inaccesible` con su causa) — mensaje con
     campo/motivo; estado íntegro anterior.
  2: E-NOEXISTE — id inexistente o búsqueda sin resultados.
Invariantes:
  - Ningún comando inicia comunicación de red SALVO
    `vigencia-verificar` (ADR-008 supera parcialmente SPEC-3/ADR-004:
    GET de sólo lectura, esquema http/https, sin redirects a otro
    host, timeout y tamaño máximo obligatorios, nunca envía datos).
  - Validación en la frontera, una sola vez, contra el contrato.
  - Escrituras atómicas: temporal + rename.
Compatibilidad: añadir comandos es compatible; cambiar semántica o
  códigos de salida exige v2.

## Modelo de estados: vigencia de una fuente

ESTADOS: desconocida --alta--> vigente | cambiada | inaccesible
TRANSICIONES:
  desconocida --vigencia-registrar(huella H, sin previa)--> vigente
  desconocida --vigencia-verificar(descarga exitosa, sin previa)-->
    vigente
  vigente --verificación(huella igual)--> vigente
  vigente --verificación(huella distinta)--> cambiada
  cambiada --verificación(huella igual a la nueva previa)--> vigente
  cualquier --archivo ilegible/inexistente--> inaccesible
  cualquier --verificación por red fallida (sin conexión, timeout,
    tamaño excedido, contenido no reconocido, redirect externo)-->
    inaccesible
INVARIANTES:
  - No existe transición hacia éxito sin archivo verificado: un
    fallo de lectura nunca produce `vigente` ni `cambiada`.
  - El historial es append-only; el estado actual es el último
    registro, nunca se sobrescribe.
  - `inaccesible` siempre registra la causa declarada.

## CONTRATO servicio-infosalud v1 (ADR-013, SPEC-9)

Servicio HTTP de SÓLO LECTURA para agentes remotos:
`python3 -m infosalud servir [--host H] [--puerto P] [--catalogo R]`;
token opcional por entorno `INFOSALUD_SERVICIO_TOKEN` (Bearer; si
está configurado, toda petición sin él responde 401). Sólo stdlib;
sin sesiones MCP ni SSE. El servicio nunca muta el catálogo ni
descarga del portal: la frescura pertenece a vigencia-verificar y
al sondeo (ADR-008).

API JSON (Content-Type application/json en todos los casos):
  GET /                  → mapa: servicio, contrato, versión, corte,
                           resúmenes por sección y vigencia, endpoints
  GET /healthz           → {ok, fuentes, ultima_verificacion}
  GET /cobertura         → índice por fuente: años detectados,
                           vigencia, última verificación y si el
                           archivo ya está descargado en disco
  GET /fuentes           → {fuentes: [registro…], total}
      parámetros: seccion, formato, q (búsqueda en id/título/notas)
  GET /fuentes/{id}      → registro completo (verificaciones incluidas)
  GET /fuentes/{id}/campos    → diccionario-de-fuente v1
  GET /fuentes/{id}/historia  → {id, verificaciones: […]}
  GET /fuentes/{id}/archivo       → binario del archivo original
      verificado (última verificación con huella y ruta local
      existente); si el sha256 recomputado en vivo difiere del
      registrado responde 409 y NO sirve el contenido
  GET /fuentes/{id}/archivo/meta  → envelope de integridad:
      {id, titulo, nombre_archivo, formato, tamanio_bytes, sha256,
       sha256_registrado, corte, fecha_descarga, url_origen_imss,
       origen: "IMSS", estado_integridad: verificado|alterado,
       estado_semantico: sin_evaluar, descarga_url}
  GET /fuentes/{id}/exportar?formato=csv|sqlite
                         → zip en memoria con los productos de
                           fuente-exportar (ADR-011) generados en
                           directorio temporal por petición
Errores HTTP: 400 E-VALID; 401 sin token válido; 404 E-NOEXISTE;
405 método no permitido; 500 fallo de entorno (catálogo ausente o
inválido). Cuerpo de error: {"error": mensaje}.

MCP (JSON-RPC 2.0; POST /mcp; modo sin sesión):
  initialize → protocolVersion "2025-06-18", capabilities {tools:{}},
               serverInfo {name "infosalud-servicio", version}
  tools/list → mapa_servicio, buscar_fuentes(q, seccion?, formato?),
               detalle_fuente(id), diccionario_fuente(id),
               historia_fuente(id), archivo_fuente(id),
               exportar_fuente(id, formato?)
  tools/call → {content: [{type: "text", text: <json>}], isError}
  Errores: -32601 método desconocido; -32602 parámetros/ herramienta
  inválidos. notifications/* → 202 sin cuerpo.

Invariantes:
  - Ningún endpoint acepta escritura; el árbol de rutas no expone
    el filesystem.
  - Toda respuesta de error es JSON con campo "error" (o error
    JSON-RPC en /mcp).
  - El token nunca se registra en bitácoras ni aparece en argv.
Compatibilidad: añadir rutas o tools es compatible; cambiar formas
de respuesta o códigos exige v2 del contrato.
