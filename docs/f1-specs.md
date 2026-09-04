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

## SPEC-8 [cubre: REQ-3, REQ-6; ADR-012]

Comportamiento: para fuentes con `url_listado`, `vigencia-verificar`
determina la última ingresada del listado histórico (heurística de
fecha embebida; fallback: primer enlace), la descarga y verifica; si
difiere de la URL registrada, actualiza `url` y deja `url_previa`.
Entradas: `vigencia-verificar <id>` sobre fuente con `url_listado`.
Salidas: las de vigencia-verificar (estado, fecha, huella, ruta
local), más `url_previa` cuando hubo rotación de versión.
Errores:
- Listado ilegible o sin enlaces a archivos → salida 1 con causa;
  NO se descarga nada ni se actualiza `url` (fail-closed).
Casos:
- DADO un listado con versiones 2024, 2025 y 2026 ENTONCES se
  descarga y verifica la de 2026; `url` del registro queda apuntando
  a ella y la verificación registra `url_previa`.
- DADO el mismo listado CUANDO no hay versión más nueva que la
  registrada ENTONCES el comportamiento es el de siempre (vigente/
  cambiada por huella) y `url` no cambia.
- DADO un listado sin enlaces legibles ENTONCES salida 1, `url`
  intacta, sin descarga.
Invariantes:
- El histórico no se descarga: sólo la última ingresada; versiones
  anteriores sólo bajo pedido expreso (D6).
- Todo giro de versión queda documentado en el historial
  (append-only: url_previa + huella nueva).

## SPEC-7 [cubre: REQ-1, REQ-6; ADR-011 — etapa 2]

Comportamiento: `fuente-exportar <id>` convierte el archivo local ya
verificado de una fuente en productos derivados consumibles —CSV o
base SQLite— conservando la evidencia de origen (id, fecha, huella)
en cada producto.
Entradas: `fuente-exportar <id> [--formato csv|sqlite]
[--destino <dir>]`; origen = archivo de la última verificación con
huella.
Salidas: CSV: `<id>__<hoja>.csv` por hoja + `<id>__evidencia.json`;
SQLite: `<id>.sqlite` con tabla por hoja y tabla `evidencia`. Resumen
en texto o `--json`.
Errores:
- E-NOEXISTE: id inexistente → salida 2.
- E-VALID: sin archivo local verificado, destino ya existe, formato
  de origen no tabular, o fallo de lectura → salida 1 con causa;
  sin productos parciales.
Casos:
- DADO una fuente con archivo xlsx verificado CUANDO se exporta a
  csv ENTONCES cada hoja produce un CSV con encabezados y datos, más
  evidencia.json con fecha y huella.
- DADO la misma fuente CUANDO se exporta a sqlite ENTONCES la base
  tiene una tabla por hoja y una tabla `evidencia` con la huella.
- DADO un destino que ya existe ENTONCES se rechaza (salida 1) sin
  alterar los productos previos.
Invariantes:
- El origen nunca se modifica; los productos son derivados y
  reproducibles; no participan en la máquina de vigencia.
- Topes declarados: 30 hojas, 200 columnas, 200 000 filas por hoja.
- Sólo stdlib (csv, sqlite3); sin red (ADR-004 en este comando).

## SPEC-9 [cubre: REQ-5; ADR-013 — v2]

Comportamiento: `python3 -m infosalud servir` levanta un servidor
HTTP de sólo lectura (stdlib) que expone el catálogo, la vigencia,
los diccionarios y las exportaciones a agentes remotos, por API JSON
(contrato `servicio-infosalud v1`) y por MCP (JSON-RPC 2.0 en
`POST /mcp`: initialize, tools/list, tools/call).
Entradas: `--host` (por defecto 127.0.0.1), `--puerto` (8081),
`--catalogo`; token opcional por entorno `INFOSALUD_SERVICIO_TOKEN`.
Salidas: JSON en todas las rutas; errores HTTP: 400 E-VALID,
401 no autorizado, 404 E-NOEXISTE, 405 método, 500 entorno.
Casos:
- DADO el servicio en pie CUANDO GET /fuentes/{id} ENTONCES responde
  200 con el registro completo (url, verificaciones con huella,
  fecha, resultado, url_previa, estructura).
- DADO un id inexistente CUANDO GET /fuentes/{id} ENTONCES 404 con
  JSON {"error": ...}.
- DADO token configurado CUANDO petición sin Authorization: Bearer
  ENTONCES 401; con token correcto ENTONCES 200.
- DADO MCP inicializado CUANDO tools/list ENTONCES lista las 6
  herramientas; CUANDO tools/call detalle_fuente con id válido
  ENTONCES contenido JSON de texto con el registro; con id
  inexistente ENTONCES resultado isError con causa.
Invariantes:
- El servicio no muta el catálogo ni descarga del portal; la
  vigencia pertenece a vigencia-verificar + sondeo (ADR-008).
- Sólo GET (API) y POST /mcp (JSON-RPC); sin rutas de filesystem.
- Sólo stdlib; sin sesiones MCP ni SSE (modo sin sesión).

## SPEC-12 [cubre: ADR-014 — fase 2: datos normalizados (nivel 2)]

Comportamiento: `GET /fuentes/{id}/datos` (y la tool MCP
`datos_fuente`) sirven las filas del archivo local verificado —
nunca del portal— segmentadas por el perfil estructural cuando
existe: encabezados, filas de datos, totales aparte (separación, no
eliminación) y `fuera_de_rango` contado (filas con contenido
después del rango declarado → `requiere_revision`: el portal
publicó filas nuevas que el perfil viejo recortaría en silencio).
Sin perfil sirve filas crudas con `perfil_aplicado: false`. El
ETag es COMPUESTO: sha256(huella_archivo + sello_del_perfil +
forma_de_respuesta) — la huella sola NO basta (corrección
adversarial #1). Cache-Control: `public, max-age=86400` con API
abierto; `private, no-store` con token (corrección #2). HEAD en
las rutas GET; X-Content-Type-Options: nosniff en toda respuesta.
Entradas: id existente con archivo verificado; parámetros
`hoja` (opcional) y `max_filas` (1..200 000, defecto 20 000).
Salidas: JSON `datos-v1` con procedencia (huella viva recomputada)
y etag; 304 sin cuerpo ante If-None-Match.
Errores:
- E-VALID: max_filas inválido, formato no tabular → 400.
- E-NOEXISTE: id, hoja no declarada en el perfil o inexistente → 404.
- E-INTEGRIDAD: sha256 vivo ≠ registrado → 409, sin contenido.
Casos:
- DADO un xlsx verificado con perfil (encabezado en fila 2, datos
  3..5, total en fila 1) CUANDO GET /datos ENTONCES 200 con datos
  segmentados, totales aparte y fuera_de_rango 0.
- DADO filas nuevas después del rango declarado CUANDO GET /datos
  ENTONCES fuera_de_rango > 0 y requiere_revision true.
- DADO el ETag recibido CUANDO se repite la petición con
  If-None-Match ENTONCES 304 sin cuerpo.
- DADO el perfil corregido con el MISMO archivo CUANDO GET /datos
  ENTONCES el ETag CAMBIA.
- DADO el archivo alterado tras la verificación CUANDO GET /datos
  ENTONCES 409 y el contenido jamás se sirve.
Invariantes:
- La procedencia viaja con el dato (sha256 vivo en cada respuesta).
- Sólo lectura; el catálogo no se muta; sin red.
- ETag compuesto; caché pública sólo con API abierto.

## SPEC-10 [cubre: REQ-7; ADR-015 — lock de catálogo]

Comportamiento: toda escritura del catálogo (`fuente-alta`,
`vigencia-registrar`, `vigencia-verificar` y su lote) se ejecuta
dentro de un lock advisory exclusivo (`fcntl.flock`) sobre el
archivo lateral `<catalogo>.lock`, adquirido antes de leer y
liberado tras guardar: ningún read-modify-write completo pisa a
otro (incidente 2026-09-02, ronda adversarial P13).
Entradas: los caminos de escritura existentes; variable de entorno
`INFOSALUD_LOCK_ESPERA` (segundos; por defecto 30) para acotar la
espera.
Salidas: las de cada comando, sin cambios.
Errores:
- E-BLOQUEADO: lock no obtenido dentro de la espera → mensaje
  claro, salida 1, catálogo sin cambios (fail-closed).
Casos:
- DADO un proceso que mantiene el lock CUANDO otro ejecuta
  `fuente-alta` ENTONCES espera y procede al liberarse, o falla
  acotado (salida 1) si la espera se agota, sin escribir.
- DADO dos altas simultáneas de ids distintos ENTONCES ambas quedan
  en el catálogo (ninguna se pierde).
- DADO el lock liberado CUANDO cualquier escritor procede ENTONCES
  el comportamiento es idéntico al previo al ADR.
Invariantes:
- El archivo de lock no se borra tras usarlo (la carrera de
  unlink/recreación es peor que un archivo vacío persistente).
- Los lectores no toman el lock: la lectura es atómica por
  `os.replace` (SPEC-3).
- Sólo stdlib (`fcntl`, POSIX).

## SPEC-11 [cubre: ADR-014 — fase 1: contrato y validador de perfil]

Comportamiento: el sistema valida y persiste perfiles estructurales
en `data/perfiles/<id>.json` (CONTRATO `perfil-de-fuente v1`): por
hoja, tipo, fila de encabezados, columnas, rango de filas de datos,
clave primaria/foráneas, columnas numéricas, filas de total y
tolerancia. La normalización futura (endpoint `/datos`) consumirá
este perfil; los totales se separan, no se eliminan (ADR-014).
Entradas: archivo JSON conforme al contrato; `id` que existe en el
catálogo y coincide con el nombre del archivo.
Salidas: perfil validado y almacenado (escritura atómica
temporal + rename).
Errores:
- E-VALID: campo faltante o no declarado, `tipo=datos` sin
  `columnas`/`filas_datos`, rango inválido, clave primaria o
  foránea fuera de `columnas`, numérica no declarada, fila de total
  dentro del rango, tolerancia <= 0 → rechazo; archivo sin cambios.
- E-NOEXISTE: consulta de perfil inexistente.
Casos:
- DADO un perfil válido de tipo datos (encabezado en fila 4, rango
  5..1742, totales en filas 1-2, tolerancia 0.005) CUANDO se
  valida ENTONCES cero errores y el archivo se persiste idéntico.
- DADO un perfil con campo no declarado ENTONCES rechazo nombrando
  el campo (esquema cerrado).
- DADO `huella_base` ausente o no-hex ENTONCES rechazo (procedencia
  obligatoria).
- DADO una fila de total dentro del rango de datos ENTONCES
  rechazo.
Invariantes:
- Esquema cerrado; `huella_base` sha256 obligatoria; `fecha` ISO.
- Los totales declarados quedan fuera del rango de datos.
- El perfil no altera la máquina de estados de vigencia.
