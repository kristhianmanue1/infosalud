# Ronda adversarial 2026-09-02 — servicio para agentes (ADR-013)

Objetivo: intentar tumbar o engañar al servicio antes de confiar en
él para la conciliación FN-19/FN-20. Método: batería de entradas
hostiles contra el servicio vivo (`0.0.0.0:8081`) más reproducción
unitaria de cada fallo. Resultado: 4 fallos reales, todos en la capa
MCP, corregidos con tests de regresión; el resto de la superficie
resistió.

## Hallazgos

| # | Ataque | Resultado antes | Después |
|---|---|---|---|
| 1 | `tools/call` con `params` lista | hilo muere, conexión cortada sin respuesta | 400 JSON-RPC -32602 |
| 2 | `arguments` lista | hilo muere (AttributeError) | 400 -32602 |
| 3 | cuerpo JSON array / texto / número | hilo muere | 400 -32600 |
| 4 | `tools/call` sin `name` | respondía isError (correcto) | sin cambio; test lo fija |
| — | cuerpo > 1 MiB | sin tope explícito | 413 |
| — | error interno imprevisto | mataría la conexión | catch-all -32603 (la conexión nunca muere) |

## Lo que resistió (sin cambios)

- Path traversal (`/fuentes/../../etc/passwd`, `%2e%2e`): 404 JSON
  limpio; el enrutado por segmentos no toca el filesystem.
- Métodos no definidos (DELETE/PUT/HEAD): 501 del `http.server`
  (contrato: sólo GET/POST).
- Catálogo corrupto/ausente: `cargar_catalogo` fail-closed → 500
  JSON (diseñado; verificado por tests existentes).
- `archivo/meta` con `ruta_local` inexistente: 404; nunca se afirma
  integridad sin archivo (sha256 recomputado en vivo, 409 si difiere).
- Query params gigantes/ajenos: ignorados o filtrados sin efecto.

## Correcciones

- `infosalud/servicio.py`: validación de tipos en `_mcp_responder`
  (petición objeto, `method` texto, `params`/`arguments` objetos),
  despacho separado (`_mcp_despachar`) con red final -32603, tope de
  cuerpo 1 MiB (413).
- `tests/test_servicio.py`: `test_mcp_entradas_hostiles_no_tumban_
  la_conexion` (6 vectores) y `test_archivo_meta_y_binario` /
  `test_archivo_meta_sin_archivo_da_404` (integridad).

## Pendiente adversarial (fuera de alcance de esta ronda)

- Parser `url_listado` multi-producto (documentado en
  `docs/mapa-portal.md`; decisión ADR pendiente).
- Lector xlsb (egresos por unidad médica): requiere ADR de lectores.
- Conciliación semántica FN-19/20: pertenece al área, no al código.

## Adenda 2026-09-02 (misma ronda, operación en vivo)

- **Carrera de escritores (hallazgo real)**: lanzar `fuente-alta`
  mientras un lote de `vigencia-verificar` corría en segundo plano
  produjo **pérdida de altas** — ambos procesos reescriben el
  catálogo completo; la escritura es atómica (sin archivos a medias)
  pero no hay lock, así que el último guardado pisa al anterior.
  Mitigación inmediata: disciplina de escritor único (nunca alta
  manual + lote en paralelo); se recuperaron las altas y quedaron
  50/50 fuentes con verificación. Candidato a ADR: lock de catálogo
  (flock) en `guardar_catalogo` antes del sondeo automatizado.
- **Descargas interrumpidas**: un ZIP de 27.5 MB quedó como `.tmp`
  al morir el proceso; se completó con `curl -C -` (el portal
  acepta rangos) y se registró con `vigencia-registrar`. El diseño
  temporal+rename evitó registrar un archivo parcial.
