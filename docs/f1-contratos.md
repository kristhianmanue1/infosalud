# F1 — Contratos de frontera y modelo de estados

> Fronteras del sistema según `skevi/docs/ai-agent-guide/02` §4-§5.
> Contratos cerrados: se acepta lo declarado, se rechaza lo demás.

## CONTRATO: registro-de-fuente v1

Esquema del registro de catálogo (archivo `data/fuentes.json`).

Entrada (campos cerrados):
  id: string [obligatorio] [patrón ^[a-z0-9-]+$] — identificador único
  seccion: string [obligatorio] [enum: "catalogos"] — sección
           Infosalud; la lista crece por versión del contrato
  titulo: string [obligatorio] [1..200 chars] — nombre de la fuente
  url: string [obligatorio] [host *.imss.gob.mx con o sin puerto
       (enmienda 2026-09-01: el portal usa :8080), esquema http o
       https] — ubicación original
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
