# F0 — Análisis inicial: Infosalud Nexus

> Proyecto: servicio local de acceso a la información de Infosalud
> (portal oficial de la División de Información en Salud, DIS) para
> usuarios humanos y sistemas de información de la DPM-IMSS.
> Clase de tarea: **Architectural** (proyecto nuevo desde cero,
> `skevi/docs/ai-agent-guide/01` §2).
> Fecha: 2026-09-01. Ejecutor: agente Cline, con dirección humana.

## 1. Problema (una frase)

La información oficial de producción médica (totales por hospital y
servicio) que Infosalud publica en formatos dispersos (Excel, CSV,
consultas en línea) se localiza y consume manualmente, sin API conocida,
lo que hace costoso mantenerla actualizada en los sistemas y flujos de
trabajo de la Dirección de Prestaciones Médicas (MOCE, IFU, catálogos,
entre otros).

## 2. Resultado observable (una frase)

Un servicio que corre en la Mac mini conectada a la intranet, donde un
humano localiza información de Infosalud (fuente, formato, ubicación y
vigencia) en segundos, y donde los sistemas de información pueden
obtener esa información por un medio mecanizado documentado, sin
intuir ni mezclar relaciones entre fuentes.

## 3. Entorno verificado

Resumen; evidencia completa en §7 (EV-*).

- Host: Mac mini M1, macOS, doble red: cable → intranet IMSS,
  wifi → internet. Ambas activas durante el análisis.
- Acceso a Infosalud: HTTP 200 vía IP de intranet `11.254.12.92`
  (resuelta por el DNS interno `10.102.10.4`). El DNS público
  (8.8.8.8) no resuelve el nombre.
- HTTPS: el host no negocia TLS en 443 (timeout); `www.imss.gob.mx`
  tampoco completa el handshake con clientes modernos. Consistente
  con lo declarado por el humano: sin certificado vigente.
- Contenido del portal (observado 2026-09-01): secciones Estadísticas
  Nacionales, Censos, Consulta Externa, Hospital (egresos, Qx, partos,
  cesáreas, UCI), Defunciones 2004–2025, Recursos (IFU, CUUMSP),
  Población (PAU, PAMF), Catálogos para los SIS (unidades, CIE-10,
  CIE-9, especialidades, semanas), Documentos Normativos, Seguimiento
  Diario/Semanal/Mensual, Capacitación, Oficios/Circulares,
  Validación de Información; herramientas enlazadas: Editor MOCE,
  Bitácora de recepción, SIMO Central, Extractor, IFU en línea,
  Día Típico, Egresos Hospitalarios, SIMOC, IDS, MMIM.
- Jerarquía organizacional verificada en el propio portal:
  IMSS → Dirección de Prestaciones Médicas → Unidad de Planeación e
  Innovación en Salud → Coordinación de Información e Inteligencia en
  Salud; portal operado por la División de Información en Salud (DIS),
  versión 2.2 del sitio.
- Runtimes disponibles: Python 3.13.5, Node.js 22.11.0, npm 11.6.2,
  git 2.50.1, Docker 28.4.0.
- Datos: totales agregados por unidad médica y servicio; el humano
  declaró que no contienen información personal.

## 4. Requerimientos

```text
REQ-1 [funcional] [fuente: humano, conversación 2026-09-01]
Enunciado: Mantener un catálogo consultable de las fuentes de
           información de Infosalud (sección, tema, formato,
           ubicación/URL y periodicidad observable).
Criterio de aceptación: dado el nombre de una sección (p. ej.
           "Catálogos"), el sistema lista al menos una fuente con
           formato y ubicación, en el entorno local.
Prioridad: imprescindible
```

```text
REQ-2 [funcional] [fuente: humano, conversación 2026-09-01]
Enunciado: Permitir localizar información por término de búsqueda
           sobre el catálogo (nombre, tema o sistema relacionado).
Criterio de aceptación: la búsqueda "IFU" devuelve las fuentes
           relacionadas con IFU en menos de 2 segundos, localmente.
Prioridad: imprescindible
```

```text
REQ-3 [funcional] [fuente: humano, conversación 2026-09-01]
Enunciado: Registrar la vigencia de cada fuente: última fecha de
           actualización observable y detección de cambio respecto
           a la consulta previa registrada.
Criterio de aceptación: dada una fuente con fecha observable, el
           sistema muestra la fecha y marca "cambió / no cambió"
           contra la consulta anterior registrada.
Prioridad: imprescindible
```

```text
REQ-4 [funcional] [fuente: humano, conversación 2026-09-01]
Enunciado: Llevar al humano desde el catálogo hasta la información
           original (enlace al portal o copia local referenciada).
Criterio de aceptación: desde el registro del catálogo, el humano
           accede al documento o dato original en 2 pasos o menos.
Prioridad: imprescindible
```

```text
REQ-5 [funcional] [fuente: humano, conversación 2026-09-01]
Enunciado: Exponer la información catalogada a otros sistemas por
           un medio mecanizado documentado (medio concreto: decisión
           de F1).
Criterio de aceptación: un cliente que no es el humano obtiene los
           datos de una fuente catalogada sin pasos manuales,
           usando solo el medio documentado.
Prioridad: deseable (horizonte v2)
```

```text
REQ-6 [funcional] [fuente: humano, conversación 2026-09-01]
Enunciado: Automatizar la actualización y monitoreo de fuentes.
Criterio de aceptación: dado un cambio observable en una fuente
           vigilada, el sistema lo detecta y lo registra sin
           intervención humana.
Prioridad: futuro (supeditado a PREGUNTA-1)
```

```text
REQ-7 [no-funcional] [fuente: humano, conversación 2026-09-01]
Enunciado: Operar íntegramente en la Mac mini, intranet-first, sin
           depender de internet para la función núcleo.
Criterio de aceptación: con la red wifi (internet) desactivada,
           las funciones de REQ-1 a REQ-4 operan sin degradación.
Prioridad: imprescindible
```

```text
REQ-8 [no-funcional] [fuente: humano, conversación 2026-09-01]
Enunciado: Trazabilidad: todo dato servido o copiado identifica su
           fuente, fecha y método de obtención.
Criterio de aceptación: 100% de los registros entregados incluyen
           fuente y fecha de obtención.
Prioridad: imprescindible
```

```text
REQ-9 [no-funcional] [fuente: humano, conversación 2026-09-01]
Enunciado: Tratar exclusivamente datos agregados (totales por
           hospital/servicio); ninguna función procesa información
           personal identificable.
Criterio de aceptación: ninguna fuente catalogada contiene datos
           personales; verificación por muestreo documentada por
           fuente dada de alta.
Prioridad: imprescindible
```

## 5. No objetivos

- No reemplaza, modifica ni re-publica Infosalud como fuente propia:
  Infosalud conserva la autoridad; este proyecto referencia y sirve.
- No implementa integraciones con sistemas consumidores (MOCE, IFU,
  SIMO, catálogos u otros): las relaciones se **proponen y
  documentan**, no se realizan aquí (decisión del humano).
- No procesa ni almacena información personal de pacientes o
  derechohabientes.
- No expone ningún servicio hacia internet: todo queda en la Mac y
  en la intranet.
- No realiza recolección automatizada del portal sin autorización
  explícita (PREGUNTA-1).
- No intuye ni infiere relaciones entre fuentes o sistemas: toda
  relación pasa por propuesta explícita revisada por el humano.

## 6. Restricciones y preguntas

### 6.1 Restricciones de entorno (confirmadas)

- R1: desarrollo iterativo e incremental, con funcionalidad útil
  desde las primeras versiones y horizonte trazado (REQ-5 y REQ-6
  son el horizonte, no la v1).
- R2: runtime disponible: Python 3.13.5, Node 22.11.0, Docker 28.4.0
  (EV-1…EV-5). Lenguaje y framework concretos: decisión de F1.
- R3: la Mac tiene doble red; el diseño no debe asumir que internet
  está disponible (fail-closed, EV-7…EV-12).

### 6.2 Preguntas cerradas (resueltas con evidencia)

- Nombre exacto del área: "Coordinación de Información e
  Inteligencia en Salud", bajo la Unidad de Planeación e Innovación
  en Salud, DPM; portal operado por la DIS (EV-13).
- ¿Hay HTTPS?: no; el host no negocia TLS (EV-11, EV-12).
- ¿Contiene datos personales?: no, según declaración del humano
  (totales por hospital y servicio); REQ-9 añade verificación por
  muestreo como salvaguarda.

### 6.3 Preguntas abiertas

> **Nota (2026-09-01):** las cuatro preguntas quedaron resueltas por
> decisión del humano ("avanza con tus recomendaciones"); las opciones
> recomendadas fueron adoptadas y se registran en §6.4. Se conservan
> como registro de la deliberación.

```text
PREGUNTA-1: ¿existe autorización institucional para consultar y/o
            copiar contenido de Infosalud de forma automatizada, y
            con qué frecuencia límite?
Por qué importa: bloquea REQ-3 (vigencia) y REQ-6 (automatización);
            sin autorización, v1 opera sólo con consulta manual
            registrada.
Opciones: (a) confirmar con DIS/CIIS y documentar el permiso;
            (b) operar en modo manual + registro hasta tenerla.
            Recomendación: (b) para v1, (a) en paralelo.
```

```text
PREGUNTA-2: contradicción de accesibilidad por resolver: una
            consulta desde internet cargó el portal completo
            (EV-8), pero el DNS público no resuelve el nombre
            (EV-10). ¿Cuál es la exposición real del portal?
Por qué importa: define la frontera de red del diseño (F1) y el
            riesgo de tratar como intranet-exclusivo algo alcanzable
            desde fuera.
Opciones: (a) preguntar a redes/DIS; (b) diseñar fail-closed
            asumiendo que puede ser alcanzable. Recomendación: (b).
```

```text
PREGUNTA-3: ¿qué sistemas consumidores son prioritarios y qué
            formato esperan (MOCE, IFU, catálogos, otros)?
Por qué importa: define el diseño de la capa "servir a sistemas"
            (REQ-5, F1).
Opciones: humano-first en v1 y consumidores en v2 (recomendado),
            o definir un consumidor piloto desde el inicio.
```

```text
PREGUNTA-4: ¿qué secciones de Infosalud entran en la v1?
Por qué importa: acota el catálogo inicial y el esfuerzo.
Opciones: (a) Catálogos + IFU + Estadísticas Nacionales;
            (b) una sola sección como piloto. Recomendación: (b)
            para cerrar el ciclo completo, luego (a).
```

### 6.4 Decisiones adoptadas (2026-09-01, decisión del humano)

- D1 [= PREGUNTA-1, opción (b)]: v1 opera en modo manual + registro:
  la herramienta no contacta la red; el humano descarga/copía por su
  medio y la herramienta registra evidencia (hash, fecha). La
  autorización institucional se gestiona en paralelo; REQ-6 (futuro)
  sigue supeditado a ella.
- D2 [= PREGUNTA-2, opción (b)]: fail-closed: se diseña asumiendo que
  el portal puede ser alcanzable desde internet; el proyecto no expone
  nada hacia fuera y su contacto con el portal es de sólo lectura,
  iniciado por el humano, fuera de la herramienta en v1.
- D3 [= PREGUNTA-3, opción (a)]: humano-first en v1; la capa "servir
  a sistemas" (REQ-5) se diseña en una F1 posterior (v2).
- D4 [= PREGUNTA-4, opción (b)]: v1 cubre una sola sección piloto:
  **Catálogos para los SIS**; el ciclo completo se cierra sobre ella
  antes de incorporar más secciones.
- D5 (2026-09-01, decisión del humano, registra `docs/adr/
  ADR-006`): el consumidor primario del sistema son **agentes de
  IA** que consumen los recursos de Infosalud; los usuarios humanos
  pasan a segunda línea. Ajusta la orientación de D3; la CLI se
  mantiene como frontera y añade salida `--json` (contrato v1.1).

## 7. Registro de evidencia

```text
EV-1: Python disponible | python3 --version → Python 3.13.5 [pass]
EV-2: Node disponible | node --version → v22.11.0 [pass]
EV-3: npm disponible | npm --version → 11.6.2 [pass]
EV-4: git disponible | git --version → 2.50.1 (Apple Git-155) [pass]
EV-5: Docker disponible | docker --version → 28.4.0 [pass]
EV-6: estado del directorio | ls infosalud → solo skevi/ (proyecto
      nuevo) [pass]
EV-7: acceso HTTP vía intranet | curl -sI
      http://infosalud.imss.gob.mx/ → HTTP/1.1 200 OK,
      Server: Microsoft-IIS/8.5, ASP.NET [pass]
EV-8: acceso desde internet | fetch_web_content
      http://infosalud.imss.gob.mx/ → página completa con contenido
      del día (contador de visitas y fechas 01/09/2026) [pass]
EV-9: DNS interno | nslookup → 10.102.10.4 resuelve
      infosalud.imss.gob.mx → 11.254.12.92 [pass]
EV-10: DNS público | dig +short infosalud.imss.gob.mx @8.8.8.8 →
      sin registro [pass]
EV-11: HTTPS infosalud | curl -v https://infosalud.imss.gob.mx/ →
      sin respuesta TLS; python ssl → TimeoutError en 443
      [fail: no hay HTTPS]
EV-12: TLS www.imss.gob.mx | curl (LibreSSL 3.3.6) → "tlsv1 alert
      protocol version"; python ssl moderno → record layer failure
      [fail: handshake no completa desde esta red]
EV-13: nombre del área | contenido del propio portal →
      "Coordinación de Información e Inteligencia en Salud", bajo
      Unidad de Planeación e Innovación en Salud, DPM; portal
      operado por la División de Información en Salud (DIS) [pass]
EV-14: inventario de secciones | contenido del portal → secciones y
      herramientas listadas en §3 de este documento [pass]
EV-15: IP efectiva de acceso | curl remoto_ip → 11.254.12.92
      (intranet); interfaz en0 172.25.0.115 [pass]
```

## 8. Definition of Ready (F0 §4.2)

- [x] problema y resultado observable, una frase cada uno (§1, §2);
- [x] requisitos con fuente, criterio verificable y prioridad (§4);
- [x] no objetivos explícitos (§5);
- [x] restricciones de entorno confirmadas con evidencia (§3, §6.1);
- [x] preguntas materiales registradas; las que cambiarían el
      diseño de v1 quedan como PREGUNTA-1…4 con recomendación
      (§6.3);
- [x] ningún requisito imprescindible sin criterio de aceptación;
- [x] sin dependencia de formatos de datos externos citados como
      evidencia: el esquema exacto de los archivos (Excel/CSV) se
      observará por muestreo en F1, no se asume aquí.

## 9. Nota para F2

El repositorio del proyecto aún no existe: `git init` y la estructura
inicial corresponden al cascarón (F2). Pendiente decidir ahí cómo se
referencia la guía Skevi, hoy clonada como directorio anidado
`infosalud/skevi/` (submódulo, copia de guía o referencia externa).


