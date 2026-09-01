# F1 — Especificaciones (Infosalud Nexus)

> Cubre los REQ imprescindibles de `docs/f0-analisis.md` §4.
> Las decisiones estructurales viven en `docs/adr/`; las fronteras,
> en `docs/f1-contratos.md`. Formato según
> `skevi/docs/ai-agent-guide/02` §2.

## SPEC-1 [cubre: REQ-1, REQ-2, REQ-4]

Comportamiento: el sistema mantiene un catálogo local de fuentes de
Infosalud consultable por listado y búsqueda; desde el registro el
humano llega a la información original (URL del portal o ruta local
referenciada).
Entradas: comandos CLI con argumentos conforme a `CONTRATO:
cli-infosalud v1`; altas de fuente conforme a `CONTRATO:
registro-de-fuente v1`.
Salidas: listados y detalles de registros, en texto plano o JSON
(`--json`, ADR-006), con código de salida 0; campos exactos según
contrato.
Errores:
- E-VALID: entrada que viola el contrato → mensaje con campo y
  motivo, salida 1, catálogo sin cambios.
- E-DUPLICADO: id ya existente → mensaje, salida 1, sin cambios.
- E-NOEXISTE: id o filtro sin resultados → mensaje, salida 2.
Casos:
- DADO un catálogo con la fuente "catalogo-cie10" CUANDO se ejecuta
  `fuente-buscar cie10` ENTONCES el registro aparece en la salida en
  menos de 2 segundos.
- DADO un alta sin campo `url` ENTONCES se rechaza con mensaje que
  nombra el campo y el motivo, y el catálogo queda sin cambios.
- DADO un registro válido CUANDO se pide su detalle ENTONCES la
  salida muestra la URL original o la ruta local en 2 pasos o menos.
Invariantes:
- El catálogo sólo contiene registros conforme al esquema cerrado;
  lo no declarado se rechaza.
- `id` único en todo el catálogo.
- Todo registro conserva su fuente y fecha de alta (REQ-8).

## SPEC-2 [cubre: REQ-3]

Comportamiento: el sistema registra, por fuente, el historial de
verificaciones de vigencia y determina si el contenido cambió desde
la verificación previa, comparando la huella del archivo que el
humano presenta.
Entradas: `vigencia-registrar <id>` junto con la ruta local del
archivo descargado por el humano; `vigencia-historia <id>`.
Salidas: estado resultante (`vigente` | `cambiada` | `inaccesible`)
con fecha y huella; historial completo en orden cronológico.
Errores:
- E-NOEXISTE: id inexistente → salida 2, historial sin cambios.
- E-VALID: archivo inexistente o ilegible → estado `inaccesible`
  registrado como fallo explícito, salida 1.
Casos:
- DADO una fuente con huella previa H CUANDO se registra una
  verificación con archivo de huella H ENTONCES el estado resultante
  es `vigente` y la historia lo registra con fecha.
- DADO la misma fuente CUANDO el archivo presenta huella distinta
  ENTONCES el estado resultante es `cambiada`.
- DADO una ruta de archivo inexistente CUANDO se registra la
  verificación ENTONCES el estado resultante es `inaccesible` y la
  salida lo declara como fallo, nunca como éxito.
Invariantes:
- El historial es append-only: ninguna verificación previa se
  modifica ni se borra.
- Todo fallo de lectura produce un estado de fallo explícito;
  nunca éxito inferido.

## SPEC-3 [cubre: REQ-7, REQ-8, REQ-9]

Comportamiento: la herramienta opera íntegramente sin red, conserva
trazabilidad completa (fuente, fecha, método) en cada registro y
trata únicamente metadatos y archivos agregados.
Entradas: los comandos de `CONTRATO: cli-infosalud v1`; archivos
locales provistos por el humano.
Salidas: las de cada comando; ningún dato se envía fuera del equipo.
Errores: cualquier fallo de entorno (archivo de catálogo ausente o
corrupto) → mensaje con la causa, salida 1, sin escrituras parciales
(escritura atómica temporal+rename).
Casos:
- DADO cualquier comando de la v1 CUANDO se ejecuta sin conexión de
  red ENTONCES su comportamiento y salida son idénticos a los con
  red disponible.
- DADO una escritura de catálogo interrumpida ENTONCES el archivo
  queda en la versión anterior completa, nunca a medias.
Invariantes:
- Ningún comando de la v1 inicia comunicación de red (salvo
  `vigencia-verificar`, acotado por ADR-008 y SPEC-4).
- Ningún comando registra datos personales en salidas ni bitácoras.

## SPEC-4 [cubre: REQ-6]

Comportamiento: bajo demanda (humano o agente) o sondeo mensual
(ADR-008), el sistema descarga la fuente de su URL registrada —GET
de sólo lectura— y registra la verificación con evidencia
verificable: fecha ISO, huella sha256, ruta local y estado.
Entradas: `vigencia-verificar <id> [--destino <ruta>]`.
Salidas: estado resultante (`vigente` | `cambiada` | `inaccesible`)
con fecha, huella y ruta local, en texto plano o `--json`; el
archivo queda disponible en destino para consumo del agente.
Errores:
- E-NOEXISTE: id inexistente → salida 2, sin descarga ni cambios.
- Fallo de red (sin conexión, timeout, tamaño excedido, redirect
  externo) o contenido no reconocido → estado `inaccesible`
  registrado con su causa, salida 1; nunca éxito inferido.
Casos:
- DADO una fuente registrada con el portal disponible CUANDO se
  ejecuta `vigencia-verificar <id>` ENTONCES el archivo queda en
  destino y la verificación registra `vigente` o `cambiada` con
  fecha y huella.
- DADO la misma fuente con huella previa H CUANDO el portal sirve
  contenido de huella H ENTONCES el resultado es `vigente`; con
  contenido distinto, `cambiada`.
- DADO el host sin conexión o sin responder dentro del timeout
  ENTONCES el estado resultante es `inaccesible` con la causa
  declarada y la salida lo presenta como fallo.
- DADO una respuesta HTTP 200 con contenido que no corresponde al
  formato declarado (p. ej. HTML para un xlsx) ENTONCES se rechaza
  y se registra `inaccesible` con esa causa.
Invariantes:
- Sólo GET, sólo al host de la URL registrada, sin redirects a otro
  host; nada se envía al portal.
- Timeout y tamaño máximo obligatorios en toda descarga.
- Descarga a archivo temporal + rename atómico: la huella nunca se
  calcula sobre un archivo a medias.
- El historial es append-only; todo intento (exitoso o fallido)
  queda registrado con fecha.

## SPEC-5 [cubre: REQ-1, REQ-6; ADR-009]

Comportamiento: el sistema mantiene, por fuente, un diccionario de
datos declarado (qué campos tiene, qué significan, cómo se usa) y
registra, de mejor esfuerzo, la estructura observada (hojas y
encabezados) en cada verificación de vigencia.
Entradas: `fuente-campos <id>` (consulta); `fuente-campos <id>
--archivo <json>` (alta/actualización conforme a
`CONTRATO: diccionario-de-fuente v1`); `vigencia-verificar` registra
`estructura`/`estructura_causa` en la verificación.
Salidas: diccionario completo en texto plano o `--json`; estructura
observada dentro de la verificación.
Errores:
- E-VALID: diccionario que viola el contrato → mensaje con campo y
  motivo, salida 1, archivo sin cambios.
- E-NOEXISTE: id inexistente, o consulta de fuente sin diccionario
  → salida 2.
Casos:
- DADO un diccionario válido CUANDO se consulta `fuente-campos <id>`
  ENTONCES la salida lista los campos con tipo y descripción (y
  `uso` si existe) en un paso.
- DADO un diccionario con campo no declarado o tipo fuera del enum
  ENTONCES se rechaza con salida 1 y el archivo queda sin cambios.
- DADO un `--archivo` cuyo `id` difiere del solicitado ENTONCES se
  rechaza (anti-huérfanos), salida 1.
- DADO una verificación exitosa de un xlsx CUANDO se registra la
  vigencia ENTONCES la verificación incluye `estructura` con hojas y
  columnas observadas; si la extracción falla, incluye
  `estructura_causa` y el `resultado` de vigencia no se altera.
Invariantes:
- El diccionario es documentación declarada; la estructura observada
  es evidencia por verificación; ninguna de las dos cambia la
  máquina de estados de vigencia.
- Extracción de mejor esfuerzo con topes declarados (30 hojas,
  200 columnas); nunca bloquea ni derriba el comando.

## SPEC-6 [cubre: REQ-1; ADR-010]

Comportamiento: `fuente-campos <id> --borrador` analiza el archivo
local ya verificado de la fuente y enriquece el diccionario sólo con
evidencia observada: valores y ejemplos muestreados por campo, y el
contenido íntegro de las hojas descriptivas (p. ej. "Metadatos y
equivalencia" del CIE-10).
Entradas: el archivo de la última verificación con huella de la
fuente; el diccionario existente o, en su ausencia, la estructura
observada para crear el esqueleto.
Salidas: diccionario actualizado con `valores`/`ejemplo` nuevos y
`metadatos` por hoja descriptiva; resumen en texto o `--json`.
Errores:
- E-VALID: sin archivo local verificado, o --archivo junto con
  --borrador → salida 1.
- E-NOEXISTE: id inexistente, o sin estructura observada para crear
  el esqueleto → salida 2/1 según causa.
Casos:
- DADO un diccionario con campos sin `valores`/`ejemplo` y un
  archivo local verificado CUANDO se ejecuta --borrador ENTONCES
  esos campos quedan con el dominio muestreado (máx 5 valores) y un
  ejemplo real; los campos ya declarados no se tocan.
- DADO una hoja descriptiva (primera fila ≥70% vacía) ENTONCES sus
  filas se registran como `metadatos` {etiqueta, contenido} con el
  nombre de la hoja.
- DADO una fuente sin diccionario pero con estructura observada
  ENTONCES --borrador crea el esqueleto y lo enriquece en un paso.
Invariantes:
- Nunca se genera ni sobrescribe una `descripcion`: el significado
  es declaración humana (ADR-009); --borrador sólo aporta
  observación.
- Lo observado reemplaza lo muestreado con fecha y huella_base
  actualizados (procedencia); nada altera la máquina de vigencia.
