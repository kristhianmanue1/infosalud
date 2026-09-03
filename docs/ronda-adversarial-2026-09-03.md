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

# Pasada 2: ataque al sistema completo propuesto (2026-09-03)

La ronda 1 atacó diseños individuales; esta pasada ataca la **cadena
completa**: paquete Postgres actualizable + dimensiones + exposición
pública (Tailscale + Cloudflare) + auditoría + perfiles a escala +
operación diaria. Afinamientos marcados como **AFINAR**.

## P1. El manifiesto `/paquete` no es atómico
El cargador lee `/paquete` y luego `/fuentes/{id}/datos` en momentos
distintos: si el sondeo actualiza una fuente entre ambas lecturas,
el cargador mezcla versiones. **AFINAR**: el cargador verifica que
el `sha256` del contenido descargado coincida con el del manifiesto;
si difiere, re-leer `/paquete` y reintentar (bucle
read-your-manifest, máx 2–3 intentos).

## P2. Semántica de retirada
Si una fuente desaparece del catálogo, desaparece del manifiesto —
pero su tabla queda huérfana en Postgres sin aviso. **AFINAR**: el
cargador compara tablas cargadas vs manifiesto y marca ausentes como
`retirada` (no borra: retiro ≠ eliminación histórica).

## P3. Versión de esquema del paquete
Un perfil nuevo puede cambiar columnas → el esquema de la tabla
cambia → los cargadores existentes fallan al hacer upsert.
**AFINAR**: el manifiesto lleva `version` (major/minor) y changelog
servido; el cargador compara versión mayor y se niega si no la
soporta (fail-closed del consumidor).

## P4. Primera carga masiva en memoria
`/datos` del PAMF (xlsx 13.8 MB) puede producir un JSON de decenas
de MB leído completo en memoria del servicio. **AFINAR** (ya
esbozado): `/datos?hoja=X` y cargador por hoja; tope de filas por
respuesta con paginación por hoja/chunk.

## P5. Dimensiones que cambian en el tiempo (SCD)
PAMF es corte junio; productividad es anual/semanal; una unidad
puede cambiar de OOAD durante el año. Un join por `clave_um` a
secas responde con la unidad "de hoy" aplicada al pasado. **AFINAR**:
`dim_unidad` con validez temporal (desde/hasta corte) y el hecho
declarando su periodo — el join FN-19 elige el registro vigente en
ese periodo (SCD tipo 2 simplificado). Es el refinamiento más
importante para que la conciliación no sea determinista-por-casualidad.

## P6. API pública sin token + binarios pesados = vector de abuso
`/fuentes/{id}/archivo` sirve ZIPs de 27 MB a cualquiera, sin
límite. Un crawler puede agotar red/disco de la Mac mini. **AFINAR**:
adelantar la decisión de token (Fase 2) o, mínimo, rate limit por IP
antes de publicar más archivos.

## P7. Doble canal público/privado — definir canónico
Tailscale (privado) y Cloudflare (público) sirven lo mismo; el
riesgo es de gobernanza: ¿cuál es la URL oficial? **AFINAR**:
documentar en `docs/despliegue-halt-to-safe.md` que
`api.halt-to-safe.dev` es canónico público y Tailscale canal
interno. Adicional: desde la intranet IMSS, el Fortinet puede
interceptar también `api.halt-to-safe.dev` — probar acceso desde la
intranet; si falla, Tailscale es el canal dentro del IMSS.

## P8. Gobernanza del dominio público
`halt-to-safe.dev` vive en una cuenta personal de Cloudflare con
contenido institucional. **AFINAR**: transferir la zona a una cuenta
del área (correo institucional) o documentar el titular y el
procedimiento de recuperación. Cloudflare soporta transferencia de
zona entre cuentas sin downtime.

## P9. Veredictos sin canal de notificación
`requiere_revision` generado por el nivel 1 no lo ve nadie si no se
consulta. **AFINAR**: los estados exponerse donde el área ya mira:
`/healthz` con conteo por `estado_semantico`, `/cobertura` con
columna de estado, y registro en AN-KLA como lección. Visibilidad
pasiva como mecanismo de notificación (sin correo, stdlib-only).

## P10. ¿Quién audita al auditor?
El informe de auditoría lo escribe el propio agente — sin integridad
ni segunda opinión. **AFINAR**: veredicto adverso (`rechazada`)
exige segunda opinión (otra pasada independiente u otro modelo)
antes de elevarse; el informe conserva ambas. Integridad del
informe: su propio sha256 registrado en el checkpoint de AN-KLA.

## P11. Perfiles a escala — plan por olas
50 fuentes × perfil manual es caro. **AFINAR**: olas — (1) los 6 del
piloto CEPI, (2) datos de consumo frecuente (series 2012–2024),
(3) resto; bloqueados (xlsb, html) quedan fuera hasta el ADR de
lectores. El borrador asistido (ADR-010) genera el perfil y el
auditor nivel 1 lo valida — flujo semi-automático.

## P12. Respaldo de `data/` — confianza vs reproducibilidad
`descargas/` NO está en git (correcto: se re-descargan del portal),
pero `perfiles/` y `auditorias/` son **trabajo acumulado** del
agente. **AFINAR**: perfiles y auditorias versionados en git (JSON
pequeños); descargas quedan reproducibles por diseño. La Mac sigue
siendo punto único de falla del servicio — aceptado explícitamente.

## P13. El lock de catálogo se vuelve crítico
Con el cargador Postgres, el sondeo y altas manuales convivirían:
**tres escritores** de `data/fuentes.json`. **AFINAR**: ADR-015 se
redacta ANTES del cargador Postgres, no después.

## Resumen de afinamientos por componente

| Componente | Afinamientos |
|---|---|
| Paquete/actualización | P1 verificación read-your-manifest, P2 retirada, P3 versión de esquema, P4 por hoja |
| Dimensiones | P5 validez temporal (SCD2), P6b aliases + ciclo vigencia |
| Exposición | P6 rate limit/token, P7 canónico documentado + prueba intranet, P8 gobernanza del dominio |
| Auditoría | P9 visibilidad pasiva, P10 segunda opinión |
| Perfiles | P11 olas |
| Operación | P12 respaldo de perfiles/auditorias, P13 lock antes del cargador |

# Pasada 4: sistema de rutas y exposición (2026-09-03, post-implementación)

Ataque al diseño recién desplegado: policy-routing del túnel por
WiFi + LaunchDaemon de rutas + doble canal público/privado.

## Verificado en vivo (sin fugas)

- Rutas aplicadas y estables: `198.41.192.0/24` y `198.41.200.0/24`
  → gateway `192.168.100.1` por `en1` ✅
- Túnel registrado por **IPv4/http2** (`--edge-ip-version 4`) ✅
- La Mac **alcanza su propia URL pública estando en la red IMSS**:
  `curl https://api.halt-to-safe.dev/healthz` → 200 (la intercepción
  Fortinet no afecta este dominio; sí afectó `pkgs.tailscale.com`).
- Servicio local intacto: `127.0.0.1:8081` → 50→70 fuentes, OK.

## Hallazgo de seguridad — H1: escalada local potencial

El LaunchDaemon de rutas corre como **root** ejecutando un script
que vive en una ruta editable por el usuario
(`~/www/infosalud/deploy/…`): cualquier proceso que modifique ese
script corre código arbitrario como root cada 60s (escalada local).

**Corrección aplicada al script**: `install` ahora copia el script a
`/usr/local/sbin/routes-cloudflare.sh` (root-owned, 755) y el
LaunchDaemon instalado ejecuta **esa copia**, no la del repo. El
repo conserva el original como fuente documental.

## Afinamientos documentados (aceptados, no implementados)

- **R1**: si el WiFi cae estando en IMSS, el túnel cae hasta volver
  el WiFi (el daemon re-aplica rutas solo cuando hay gateway en
  en1). Aceptado: la alternativa es enrutar por el firewall que
  bloquea.
- **R2**: ventana de interrupción ≤60s al cambiar de red WiFi
  (StartInterval del daemon). Aceptado; reducible a 15s si molesta.
- **R3**: Tailscale sigue offline en red IMSS (relays bloqueados);
  enrutar los rangos DERP es complejo y dinámico — se queda como
  limitación: Tailscale funciona fuera del IMSS.
- **R4**: deriva de plists — `deploy/` es canónico; tras editar
  ahí, recopiar a `~/Library/LaunchAgents` y `launchctl` reload.

## Cadena de arranque final (post-ronda)

login → OrbStack → contenedor `1nf0541ud` (8081) → cloudflared
(LaunchAgent, IPv4/http2) → **rutas cloudflared por WiFi
(LaunchDaemon root, script root-owned en /usr/local/sbin)** →
Tailscale userspace (LaunchAgent).

# Pasada 3: entrega de preservación CEPI (2026-09-03)

Ataque a la entrega de preservación (contrato con parent_source_id/
aliases/corte_declarado + registro masivo de 14 hijos):

- **F1 — referencias colgantes**: `fuente-alta` aceptaba
  `parent_source_id` apuntando a fuentes inexistentes. Corregido:
  el alta valida que el parent exista en el catálogo (fail-closed,
  test de regresión).
- **Contrato sin documentar**: los 3 campos nuevos no estaban en
  `docs/f1-contratos.md`. Corregido (enmienda compatible).
- **Huellas repetidas**: verificadas — todas son historial
  append-only de la misma fuente; **sin duplicados entre fuentes
  distintas**.
- **parent_source_id en catálogo real**: 14, todos resuelven.
