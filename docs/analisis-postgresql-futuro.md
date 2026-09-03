# Análisis: camino a PostgreSQL y paquete de tablas actualizable
# (futuro, 2026-09-03)

Pregunta: ¿la arquitectura actual sirve para incorporar después un
servicio de base de datos en Postgres, para consultas rápidas o para
entregar a otros sistemas un **paquete de tablas actualizable al
consultar este servidor**? Respuesta corta: **sí — el diseño ya
estableció las bases exactas que Postgres necesita**, y lo que falta
es acotado. Este documento fija esas bases.

## 1. Por qué el diseño actual ya es "Postgres-ready"

El nivel 2 propuesto (datos normalizados + perfiles + dimensiones)
es, en términos de base de datos, un **modelo de staging + dimensiones**:

| Concepto del servicio | Equivalente en Postgres |
|---|---|
| Huella sha256 por fuente | columna de sincronización + clave de idempotencia |
| Perfil estructural (hoja, rango, columnas, claves) | DDL: esquema, tipos y constraints por tabla |
| Dimensiones canónicas (`/dimensiones/*`) | tablas de dimensión (`dim_unidad`, `dim_servicio`, `dim_periodo`) |
| Cobertura de clave | control de calidad en la carga (filas huérfanas) |
| `fuente-exportar` SQLite (ADR-011) | el mismo patrón, ya implementado, para un motor |
| Sondeo launchd (invalida caché por huella) | disparador del proceso de actualización |

Es decir: **no hay que rediseñar nada** — hay que materializar.

## 2. El error a evitar: Postgres detrás de la API v1

La frontera del sistema es el **contrato HTTP** (ADR-013). Si el
servicio pasa a consultar Postgres directamente, se rompen: stdlib
(requiere driver), fail-closed, y el principio read-only. La
arquitectura correcta invierte la flecha:

```
Portal → infosalud (API, única frontera) → Postgres del consumidor
              (huella/ETag)                    (proceso actualizador)
```

**Postgres es un consumidor de la API, igual que un agente** — solo
que en lugar de guardar JSON, carga tablas. Un proceso actualizador
(por ejemplo, un contenedor Postgres en OrbStack + un script de
carga, ambos fuera del paquete stdlib) que:

1. consulta `/cobertura` y los ETag;
2. baja solo lo que cambió (`/fuentes/{id}/datos`);
3. hace upsert idempotente a `hechos_<fuente>` y `dim_*`,
   usando la huella como versión;
4. deja trazabilidad (corte, huella, resultado) en una tabla de
   sincronización.

Así "paquete de tablas actualizable al consultar este servidor" se
cumple **sin que el servidor sepa que existe Postgres**.

## 3. El paquete versionado (lo nuevo que sí se construye aquí)

Para que otros sistemas carguen el paquete, la API debe exponer el
**manifiesto del paquete**: qué tablas existen, su esquema, su
huella origen y su versión. Propuesta (futuro, contrato v2):

```json
GET /paquete
{"paquete": "infosalud", "version": 3,
 "tablas": [
   {"tabla": "dim_unidad", "fuente": "catalogo-ooad-subdelegaciones",
    "huella": "b0d9d26b…", "filas": 214},
   {"tabla": "hechos_pamf_um", "fuente": "poblacion-pamf-siais-2025",
    "huella": "6e4a3b95…", "filas": 1738}
 ]}
```

Con eso, cualquier sistema (Postgres, SQLite, Excel) sincroniza por
diferencia de huellas — el mismo mecanismo ETag, elevado a paquete.
La base ya está: `/cobertura` es el 80% de este manifiesto.

## 4. Bases a establecer HOY (baratas, sin Postgres)

1. **Claves estables** — los perfiles deben declarar
   `clave_primaria` con nombres normalizados (snake_case), no los
   encabezados crudos del Excel. Ya está en el diseño de perfiles.
2. **Tipos declarados en el perfil** — texto/número/fecha por
   columna: es el DDL futuro. Cae de la corrección del parser
   numérico (ronda adversarial 2026-09-03, hallazgo 5).
3. **Nombres de tabla deterministas** — `hechos_<id>` y
   `dim_<nombre>`; nada de nombres derivados de hojas con espacios.
4. **SQLite como imagen del paquete** — `fuente-exportar` ya genera
   SQLite por fuente; consolidarlo en una sola base por paquete es
   un paso intermedio barato que sirve HOY a sistemas sin Postgres.

## 5. Cuándo sí, cuándo no

- **Sí**: varios sistemas consultando con filtros/joins frecuentes;
  históricos grandes (series 2012–2024); consultas interactivas.
- **No todavía**: mientras el volumen sea 50 archivos y el
  consumidor principal sean agentes puntuales — la API + SQLite
  exportado cumple. Postgres sin necesidad es complejidad (respaldo,
  versiones, administración) que no resuelve un problema presente.

## 6. Método y estado de los ADRs

Sí: seguimos el método skevi registrando decisiones en `docs/adr/`
(inmutables: cambiar una decisión crea ADR nuevo), con contratos
versionados y tests DADO/CUANDO/ENTONCES. Estado:

| ADR | Tema | Estado |
|---|---|---|
| 001–011 | runtime, catálogo, CLI, red, ámbito, agentes, memoria, vigencia, diccionario, borrador, exportación | aceptados |
| 012 | listados históricos url_listado | aceptado (parser multi-producto pendiente de decisión) |
| 013 | servicio agentes HTTP+MCP | aceptado (con despliegue público halt-to-safe.dev) |
| **014 (aceptado)** | perfiles estructurales + nivel de datos normalizado + auditoría por agente (con correcciones adversariales: ETag compuesto, veredicto advisory, parser numérico, fuera_de_rango) | fase 1 implementada: contrato perfil-de-fuente v1 + validador + SPEC-11; fases 2-4 pendientes |
| **015 (candidato)** | lock de catálogo (carrera de escritores) | pendiente |
| (futuro) | paquete de tablas + Postgres como consumidor | se documenta como este análisis; ADR solo al ser decisión inmediata |

Regla aplicada: no se redacta el ADR de Postgres hasta que la
decisión sea inmediata; este documento deja las bases para que ese
ADR futuro sea trivial.