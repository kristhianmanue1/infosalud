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
  vigencia-registrar <id> --archivo <ruta>: registra verificación
    comparando la huella sha256 del archivo presentado con la previa
  vigencia-historia <id>: lista el historial cronológico

Salida: texto plano; código 0 en éxito.
Errores:
  1: E-VALID o E-DUPLICADO, o fallo de entorno (catálogo ausente o
     corrupto) — mensaje con campo/motivo; estado íntegro anterior.
  2: E-NOEXISTE — id inexistente o búsqueda sin resultados.
Invariantes:
  - Ningún comando inicia comunicación de red (SPEC-3).
  - Validación en la frontera, una sola vez, contra el contrato.
  - Escrituras atómicas: temporal + rename.
Compatibilidad: añadir comandos es compatible; cambiar semántica o
  códigos de salida exige v2.

## Modelo de estados: vigencia de una fuente

ESTADOS: desconocida --alta--> vigente | cambiada | inaccesible
TRANSICIONES:
  desconocida --vigencia-registrar(huella H, sin previa)--> vigente
  vigente --verificación(huella igual)--> vigente
  vigente --verificación(huella distinta)--> cambiada
  cambiada --verificación(huella igual a la nueva previa)--> vigente
  cualquier --archivo ilegible/inexistente--> inaccesible
INVARIANTES:
  - No existe transición hacia éxito sin archivo verificado: un
    fallo de lectura nunca produce `vigente` ni `cambiada`.
  - El historial es append-only; el estado actual es el último
    registro, nunca se sobrescribe.
  - `inaccesible` siempre registra la causa declarada.
