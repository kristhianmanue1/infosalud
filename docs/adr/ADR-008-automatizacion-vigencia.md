# ADR-008: Automatización de vigencia (REQ-6) y consumo por agentes

Estado: aceptado (autorización humana 2026-09-01; decisión 1-4 y
horizonte por etapas declarados por el humano, ronda adversarial
aplicada)
Fecha: 2026-09-01

Contexto: PREGUNTA-1 resuelta a favor (D6, 2026-09-01): el nivel
central de la DPM tiene autorización para consumo de los catálogos
oficiales, lo que desbloquea REQ-6 con prudencia (sólo lectura,
frecuencia contenida, sin re-publicación). ADR-004 prohibió toda
comunicación de red en la v1; es inmutable, así que la automatización
exige un ADR nuevo que la supere parcialmente. Adicionalmente, el uso
real esperado no es el sondeo programado sino el consumo bajo demanda
por agentes de IA (coherente con ADR-006).

Decisión:
  1. Se supera parcialmente ADR-004: se permite comunicación de red
     de SÓLO LECTURA (HTTP GET) hacia el host del portal
     (infosalud.imss.gob.mx:8080), exclusivamente para descargar
     archivos de fuentes ya registradas en el catálogo.
  2. Frecuencia límite: sondeo automático MENSUAL por fuente
     vigilada, más verificación BAJO DEMANDA explícita (humano o
     agente) cuando se requiera. Prohibida la re-publicación de lo
     descargado (D6). Todo intento de verificación —exitoso o
     fallido— queda registrado en el historial append-only; para uso
     automatizado se observa cadencia mínima de una hora por fuente
     (límite blando, no enforcement de código en v1).
  3. Implementación stdlib-only (urllib.request), sin dependencias
     nuevas (ADR-001). Fail-closed: sin red, timeout o descarga
     fallida registra `inaccesible` con causa declarada; nunca éxito
     inferido (invariantes de docs/f1-contratos.md). Timeout
     explícito y corto en toda conexión (la red lenta no puede
     colgar al agente).
  4. Primera fuente vigilada real: `catalogo-cie10-simf-maestro`
     (URL confirmada en data/fuentes.json).
  5. Reenfoque del valor (d-4): la capacidad primaria es servir
     insumos a agentes bajo demanda — listado actualizado de
     catálogos, estado de vigencia, detalle y ruta local del archivo
     para su consumo (salida --json, ADR-006). El sondeo mensual es
     secundario y de baja utilidad esperada; la verificación bajo
     demanda se implementa primero.
  6. Salvaguardas de la descarga (todas fail-closed): descarga a
     archivo temporal + rename atómico (invariante del contrato: la
     huella nunca se calcula sobre un archivo truncado); tamaño
     máximo declarado; verificación mínima de contenido antes de
     registrar (p. ej. firma zip para xlsx) para rechazar respuestas
     HTTP 200 con páginas de error; no se siguen redirecciones
     fuera del host autorizado.
  7. Riesgo aceptado y declarado: el portal no ofrece TLS (EV-11);
     la huella sha256 registra QUÉ se recibió, no autentica DE QUIÉN
     vino. Mitigación: red de intranet institucional, sólo lectura,
     evidencia auditable en historial; discrepancia sospechosa queda
     como `cambiada` para revisión humana.
  8. Orden de implementación: primero el comando de verificación
     bajo demanda; el sondeo mensual después, como pieza separada
     (programador local launchd en la Mac mini, coherente con
     REQ-7) que invoca el mismo comando.

Horizonte por etapas (declarado por el humano, 2026-09-01):
  - Etapa 1 (este ADR): extracción de sólo lectura de cada fuente
    junto con su evidencia verificable — fecha ISO de verificación,
    huella sha256, ruta local y estado de vigencia — puesta a
    disposición vía CLI (`--json`, ADR-006). Ya soportada por
    `vigencia-registrar`/`vigencia-historia` y `fuente-detalle`.
  - Etapa 2 (siguiente): procesamiento de los insumos a formatos
    derivados — CSV y SQL — conservando la evidencia de origen
    (huella y fecha) en cada producto. Cubrible con stdlib
    (`csv`, `sqlite3`); exigirá ADR propio para el formato/esquema.
  - Etapa 3 (futuro): base de datos dedicada y puesta a disposición
    vía API. Supera ADR-003 (CLI local) y abre una superficie de
    red de SERVICIO distinta de la de extracción aquí autorizada;
    exigirá ADR nuevo con su propia evaluación de riesgo.

Alternativas descartadas:
  - Mantener cero red (ADR-004 estricto): mantiene REQ-6 bloqueado
    indefinidamente pese a existir autorización documentada (D6);
    contradice el criterio de aceptación de REQ-6.
  - Sondeo diario o semanal: excede la "frecuencia contenida" de D6
    sin requisito que lo justifique; tráfico plano observable
    (EV-11) sin beneficio proporcional.
  - Librería de red de terceros (p. ej. requests): viola ADR-001;
    urllib.request de stdlib cubre el GET necesario.
  - Verificación programada como capacidad primaria: el uso real
    declarado por el humano (2026-09-01) es la petición de insumos
    por agentes; el sondeo aporta poco con frecuencia mensual.

Consecuencias: gana REQ-6 desbloqueado con el modo de operación que
realmente se usará (agente pregunta, sistema entrega insumo y
evidencia de vigencia). Pierde la pureza "cero sockets": superficie
de red nueva pero acotada (sólo lectura, un host, sin redirects
externos, frecuencia límite declarada, fail-closed con timeout).
ADR-004 queda vigente en todo lo no superado aquí (nada escribe a la
red; prohibido importar librerías de red de terceros). El contrato
cli-infosalud v1.1 admite añadir comandos (p. ej.
`vigencia-verificar <id>`) y causas nuevas de `inaccesible` (fallo
de red) sin cambiar la semántica existente: ambas son adiciones
compatibles; cambiar semántica vigente exigirá v2.
