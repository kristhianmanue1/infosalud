# ADR-009: Diccionario de datos de las fuentes (etapa 2, primer paso)

Estado: aceptado (autorización humana 2026-09-01: "sí, con ronda
adversarial para ampliar y afinar")
Fecha: 2026-09-01

Contexto: auditoría de consumo (pregunta del humano 2026-09-01): un
agente puede listar y vigilar fuentes, pero no sabe qué columnas
tiene un catálogo, qué significa cada campo ni cómo usarlo. Las
`notas` son texto libre inconsistente (8/23 fuentes sin notas; otras
sólo con fecha). El contrato admite añadir campos y comandos
opcionales sin subir versión. Decisiones refinadas por ronda
adversarial (8 hallazgos).

Decisión:
  1. CONTRATO diccionario-de-fuente v1: un archivo por fuente en
     `data/diccionarios/<id>.json` (fuera de fuentes.json para no
     hinchar el catálogo único ni mezclar evidencia con
     documentación). Esquema cerrado: descripcion, uso, huella_base,
     fecha y campos[] {nombre, tipo enum (texto|numero|fecha|clave|
     booleano|otro), descripcion, obligatorio, valores, ejemplo}.
  2. Comando `fuente-campos <id> [--archivo <json>]`: consulta
     (texto o --json; salida 2 si no existe la fuente o el
     diccionario) y alta/actualización validada en frontera
     (salida 1 si inválido). Exige que el `id` exista en el catálogo
     y coincida con el del archivo (anti-huérfanos).
  3. Estructura observada: `vigencia-verificar` registra en la
     verificación, de mejor esfuerzo, `estructura` [{hoja, columnas}]
     extraída del xlsx (stdlib: zipfile+XML; primera fila por hoja;
     topes 30 hojas / 200 columnas) y `estructura_causa` si no pudo.
     Un fallo de extracción NUNCA altera el estado de vigencia:
     la extracción es evidencia, no condición de éxito (invariantes
     del modelo de estados intactos).
  4. Diccionario declarado ≠ estructura observada: el primero es
     intención documental (humano/área); la segunda, evidencia por
     verificación. El drift de columnas se reporta; no crea estado
     nuevo en la máquina de vigencia (`cambiada` ya cubre el cambio
     de archivo).
  5. Deuda documental saldada en la misma rama: `--help` y README
     reflejan la red de ADR-008 y los comandos vigentes.

Alternativas descartadas:
  - Diccionario dentro de registro-de-fuente (fuentes.json): hincha
    el archivo único, complica merges y mezcla evidencia verificable
    con documentación editable.
  - Parseo completo del xlsx (celdas, fórmulas, celdas combinadas):
    desproporcionado con stdlib; para describir estructura bastan
    hojas y encabezados.
  - Nuevo estado de vigencia por drift de columnas: duplica lo que
    `cambiada` ya registra; el drift es evidencia adicional.
  - Diccionario autogenerado sin humano: los significados son
    conocimiento del área; el sistema levanta la estructura, el
    sentido lo declara el humano.

Consecuencias: gana respuestas verificables a "¿qué campos tiene
esta fuente y cómo se usa?" (CLI/--json, ADR-006) y evidencia de
estructura por verificación. Pierde simplicidad: un archivo más por
fuente y un lector xlsx mínimo que mantener; la calidad del
diccionario depende del levantamiento humano, que el esqueleto
automático (columnas observadas) abarata pero no sustituye.
