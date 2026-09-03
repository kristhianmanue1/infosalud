# Ronda adversarial de diseño — 2026-09-03

Objetivo: atacar los **diseños propuestos** (perfiles estructurales,
dimensiones canónicas, reconciliación, auditoría por agente, ETag,
multi-proyecto) *antes* de implementarlos, más sondas a la
implementación vigente. Separado de la ronda técnica de 2026-09-02
(docs/ronda-adversarial-2026-09-02.md).

## Veredicto por diseño atacado

### 1. ETag = huella (análisis de arquitectura §4) — FALLA TAL CUAL
- El JSON de `/datos` depende de **dos** entradas: huella del
  archivo **y versión del perfil**. Si se corrige el perfil con el
  mismo archivo (huella idéntica), el ETag no cambia → cachés
  sirven datos viejos con confianza inmerecida.
- **Corrección al diseño**: `ETag = sha256(huella + sha_perfil +
  forma_de_respuesta)`. La huella sola solo sirve para `/archivo`.

### 2. Cache-Control public + token futuro — CONFLICTO LATENTE
- Si mañana se activa `INFOSALUD_SERVICIO_TOKEN` y las respuestas
  llevan `Cache-Control: public`, Cloudflare puede cachear la
  respuesta de un agente autenticado y servírsela a uno no
  autenticado.
- **Corrección**: con token activo → `Cache-Control: private, no-store`
  (o `Vary: Authorization`); `public` solo mientras el API sea abierto.

### 3. Auditoría con veredicto automático `rechazada` — DEMASIADO PODER
- El diseño original dejaba que el veredicto del agente cambiara
  `estado_semantico` a `rechazada_por_auditoria` públicamente: un
  modelo no determinista tomando una decisión de gobernanza que
  bloquea datos ante el área, sin humano de por medio.
- **Corrección**: el agente solo puede marcar `requiere_revision`.
  `rechazada` exige confirmación del área/humano. El informe siempre
  registra modelo, versión y fecha. (Adenda a análisis-datos §D.)

### 4. Perfil desactualizado vs archivo nuevo — PÉRDIDA SILENCIOSA
- Portal publica versión nueva con 200 filas más; el perfil viejo
  declara rango 5–1742 → la normalización **recorta sin avisar**.
- **Corrección**: tras normalizar, contar filas con contenido fuera
  del rango declarado y exponerlas (`fuera_de_rango: n`); si n > 0 →
  `requiere_revision`. El nivel 1 de auditoría (diff estructural por
  cambio de huella) es el disparador natural.

### 5. Reconciliación numérica — FRÁGIL SI SE SUBESTIMA
- `leer_filas` entrega todo como texto: "1,234.56", totales por
  columna, subtotales intercalados por región, hojas de meses
  separadas. Un `fila_total` mal declarado produce falsos
  "no reconciliado" y desconfianza en el sistema.
- **Corrección**: parser numérico con normalización (comas de
  millar, símbolos), perfil que declare qué columnas son numéricas y
  tolerancia explícita (ej. ±0.5%), y soporte de múltiples filas de
  total/subtotal. Fase de perfil inicial = la parte cara; el borrador
  asistido (ADR-010) es el punto de partida.

### 6. Dimensiones canónicas — DOS HUECOS
- **Aliases**: cada sistema nombra la unidad a su modo (SIAIS vs
  SIMO vs MOCE); la dimensión necesita tabla de alias, no solo
  claves canónicas (el conversor de servicios existe; para unidades
  habría que construirlo o confirmar que el catálogo OOAD basta).
- **Dimensión vencida**: `catalogo-ooad` está en corte feb 2025;
  unidades abiertas en 2026 no resolverán → cobertura caerá sin que
  sea culpa del dataset. La dimensión necesita su **propio ciclo de
  vigencia** y fecha de corte visible en el endpoint.

### 7. Cobertura de años — SEMÁNTICA MEZCLADA (hallazgo en vivo)
- La regex actual detecta "años" dentro de fechas de descarga y
  nombres de archivo: `…Junio_2025_ver1_2026-02-24` reporta 2026 por
  la fecha de publicación, no por cobertura. Además coincide dentro
  de números largos.
- **Corrección**: extraer años solo del `titulo` con límites de
  palabra, y que el **perfil declare el año de cobertura
  explícitamente**; `/cobertura` distingue `anios_cobertura` vs
  `fecha_publicacion`.

### 8. Doble servidor en 8081 — PELIGRO OPERATIVO
- Contenedor (OrbStack) y host `nohup` pueden querer el mismo
  puerto: si OrbStack arranca mientras el host instancia vive, el
  contenedor entra en crash-loop. Hoy convive el host de respaldo
  porque OrbStack está detenido.
- **Corrección**: regla de escritor único **también para servir**:
  o contenedor (producción) o host (respaldo manual), nunca ambos;
  el `docker-compose` podría reclamar el puerto como canario.

### 9. Duplicación `~/.cloudflared/config.yml` vs `deploy/` — DERIVA
- Dos copias del ingress = una mentirá tarde o temprano.
- **Corrección**: `deploy/cloudflared-config.yml` es el canónico;
  el archivo de ~/.cloudflared es un symlink o se sincroniza con un
  script de despliegue que además recarga el LaunchAgent.

### 10. Validador de URLs — RESISTE (sonda)
- URL con credenciales embebidas (`http://user:pass@host`): rechazada.
- Vigilancia futura: rechazo explícito de userinfo y de rutas con
  `..` en la URL registrada.

## Saldos de la ronda

- 2 correcciones al diseño (ETag compuesto, veredicto advisory).
- 4 requisitos nuevos de diseño (fuera-de-rango visible, parser
  numérico + tolerancia, alias/ciclo de dimensiones, semántica de
  años en cobertura).
- 2 riesgos operativos documentados (doble servidor, deriva de
  config).
- 1 sonda de validador sin fuga.

Ningún diseño propuesto se cae entero; todos requieren las
correcciones de esta ronda antes de llegar a ADR-014.
