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
- Ningún comando de la v1 inicia comunicación de red.
- Ningún comando registra datos personales en salidas ni bitácoras.
