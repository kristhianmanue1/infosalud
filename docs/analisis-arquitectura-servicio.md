# Análisis de arquitectura: cómo servir mejor la información
# (servicio para agentes, ADR-013)

Fecha: 2026-09-03. Contexto: el servicio funciona y ya es consumido
por un agente CEPI (archivos originales servidos por URL). Este
análisis evalúa el estado actual contra buenas prácticas de
arquitectura de software y propone cómo evolucionar el *servicio de
información* — no solo de archivos.

## 1. Estado actual (inventario)

- API JSON de sólo lectura: `/`, `/healthz`, `/cobertura`,
  `/fuentes` (+filtros), `/fuentes/{id}`, `/campos`, `/historia`,
  `/archivo` (binario), `/archivo/meta`, `/exportar` (zip ADR-011).
- MCP sobre `POST /mcp`: 8 herramientas tipadas.
- Seguridad: read-only, confinamiento de perímetro, token opcional
  (hoy desactivado), TLS por Cloudflare/Tailscale, fail-closed.
- Datos: archivos originales tal como los publica el portal
  (xlsx/xls/zip/html), con huella sha256 y verificacions append-only.
- Autoarranque: OrbStack → contenedor 1nf0541ud + host de respaldo;
  túneles Tailscale y Cloudflare (halt-to-safe.dev) multi-proyecto.

## 2. Evaluación contra buenas prácticas

| Dimensión | Práctica esperada | Estado | Nota |
|---|---|---|---|
| Contratos y versionado | contrato explícito, compatibilidad additive | ✅ | servicio-infosalud v1 + ADR |
| Descubrimiento | self-describing / tools | ✅ | mapa + MCP tools/list |
| Errores uniformes | problem-details (RFC 9457) | ⚠️ | hoy `{"error"}` propio; suficiente, estandarizable |
| Autenticación | obligatoria en superficie pública | ⚠️ | token implementado, **no activado** |
| Caching condicional | ETag + 304 Not Modified | ❌ | **oportunidad principal**: la huella sha256 ES un ETag natural |
| Content negotiation | JSON/CSV según Accept | ⚠️ | hoy formato fijo por ruta |
| Datos normalizados | servir datos, no solo contenedores | ❌ | los agentes deben parsear xlsx por su cuenta |
| Paginación | para colecciones que crecen | ⚠️ | 50 fuentes hoy; trivial al crecer |
| Rate limiting | protección básica | ❌ | túnel público lo hace deseable |
| Observabilidad | métricas + request-id + bitácora | ⚠️ | bitácora mínima; sin `/metrics` ni correlación |
| Seguridad HTTP | headers (CSP no aplica a API; X-Content-Type-Options sí) | ❌ | menor |
| Idempotencia | GET idempotente | ✅ | toda la API es read-only |
| MCP best practices | tools tipadas, isError, fail-closed | ✅ | confinamiento + catch-all verificados en rondas adversariales |

## 3. Diagnóstico central

El servicio hoy es un **servidor de archivos con metadatos de
calidad excepcional** (huella, vigencia, procedencia, integridad
en vivo) — pero los consumidores siguen teniendo que **descargar
contenedores opacos** (xlsx) y parsearlos ellos. La mejor práctica
para servir información a agentes es ofrecer **tres niveles del
mismo dato**, con la misma garantía de procedencia:

- **Nivel 1 — archivo original** (ya existe): auditoría y
  reproducibilidad; `sha256` = verdad.
- **Nivel 2 — datos normalizados** (propuesto): JSON/CSV con las
  filas ya extraídas del archivo verificado — el agente consulta,
  no parsea. El lector `estructura.leer_filas` ya existe (usado por
  ADR-010/011): reutilización directa.
- **Nivel 3 — vistas agregadas** (futuro): consultas dominio
  (`/cobertura` fue el primero); p. ej. totales por unidad/periodo
  para FN-19/20 sin bajar el archivo.

Regla de oro: **el nivel 2/3 siempre declara su `sha256` de origen**
— la procedencia nunca se pierde al normalizar.

## 4. Caching: la sinergia exacta de este sistema

Cada dato derivado es **determinista respecto a la huella**: si el
archivo no cambió (huella igual), la respuesta es idéntica. Entonces:

- `ETag: "<huella-sha256>"` en `/archivo`, `/archivo/meta` y
  `/datos` — el agente manda `If-None-Match` y recibe `304` sin
  transferir nada.
- `Cache-Control: public, max-age=86400` (o hasta el siguiente
  sondeo del launchd) — los agentes y Cloudflare cachean gratis.
- El **sondeo mensual/semanal** ya existente es el invalidador
  natural: cuando `vigencia-verificar` detecta versión nueva, la
  huella cambia y toda la caché se invalida sola.

Esto convierte el patrón "sondeo → huella → caché" en una
arquitectura de **data products con invalidación por contenido**,
sin base de datos ni colas: stdlib puro.

## 5. Roadmap propuesto

### Fase 1 — servir información (alta valeur, ~1 sesión)
1. `GET /fuentes/{id}/datos` → JSON normalizado por hoja
   (`{hoja: [[col,…],[fila,…]]}`) leído del archivo verificado,
   con `ETag` = huella y `304` ante `If-None-Match`.
2. Tool MCP `datos_fuente(id, hoja?)` → mismo contenido.
3. `HEAD` en todas las rutas GET + `Cache-Control` + `ETag`.
4. Headers de seguridad mínimos (`X-Content-Type-Options: nosniff`).
5. Tope de filas configurable (reusar MAX_FILAS=200k de exportar).

### Fase 2 — endurecer superficie pública
1. Decidir y activar token (o dejar público por decisión del área).
2. Rate limit simple por IP (contador en memoria; stdlib).
3. `GET /metrics` (counters por ruta/código) + `X-Request-Id`.
4. Estandarizar errores a RFC 9457 (`application/problem+json`)
   — manteniendo `{"error"}` como alias v1.

### Fase 3 — plataforma multi-proyecto (usa halt-to-safe.dev)
1. Plantilla de proyecto nuevo: puerto propio + bloque ingress en
   `deploy/cloudflared-config.yml` + ruta DNS (ya documentado).
2. Índice raíz `halt-to-safe.dev` → catálogo de servicios.
3. ADR lock de catálogo (carrera de escritores — ya detectada).
4. ADR parser `url_listado` multi-producto / lector xlsb.

## 6. Principios que NO se negocian

- Sólo stdlib; sin dependencias nuevas.
- Read-only estricto; fail-closed ante catálogo inválido.
- La procedencia viaja con el dato (sha256 en todo nivel).
- Cambios de forma de respuesta ⇒ versión nueva del contrato
  (compatible ⇒ v1 sigue).
- Toda ampliación de superficie pasa por ADR + tests DADO/CUANDO/
  ENTONCES.
