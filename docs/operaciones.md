# Runbook de operaciones — qué corre dónde y fallas comunes

## 1. Servicios en ejecución (por red)

| Red de la Mac | Servicio local (:8081) | Túnel Cloudflare | Tailscale |
|---|---|---|---|
| Solo IMSS (cable) | ✅ host o contenedor | ❌ (firewall: sin egreso 7844) | ❌ (relays bloqueados) |
| IMSS + WiFi | ✅ contenedor `1nf0541ud` (canónico) | ✅ (rutas policy-routing por en1) | ⚠️ según relays |
| Solo WiFi / hogar | ✅ contenedor | ✅ | ✅ |

Canónico público: `https://api.halt-to-safe.dev`. Interno:
`http://172.25.0.115:8081`. Mac: `1nf0541ud.orb.local:8081`.

## 2. Cómo iniciar / detener

```bash
# Servicio en contenedor (producción, restart: always)
docker compose up -d --build          # levantar/reconstruir
docker compose down                   # detener

# Servicio en host (respaldo) — NUNCA junto con el contenedor
pkill -f 'infosalud servir'           # detener
nohup python3 -m infosalud servir --host 0.0.0.0 --puerto 8081 &

# Túnel Cloudflare (rutas policy-routing por WiFi)
sudo deploy/routes-cloudflare.sh install   # rutas + daemon (root)
launchctl load ~/Library/LaunchAgents/com.infosalud.cloudflared.plist
launchctl unload ~/Library/LaunchAgents/com.infosalud.cloudflared.plist  # pausar (p. ej. en red IMSS)

# Tailscale userspace
launchctl load ~/Library/LaunchAgents/com.infosalud.tailscaled.plist

# Sondeo mensual de vigencia (launchd)
# ver docs/sondeo-launchd.md
```

## 3. Fallas comunes → solución

| Síntoma | Causa | Solución |
|---|---|---|
| `api.halt-to-safe.dev` no responde en red IMSS | Fortinet bloquea egreso 7844 (QUIC/UDP y TCP) | Esperado. Usar `http://172.25.0.115:8081` (intranet) o salir de la red IMSS y `launchctl load` del túnel. NO forzar reintentos (riesgo de ban) |
| `curl https://api…` falla con error SSL 60 | Intercepción TLS Fortinet sobre el dominio, solo afecta al curl local en red IMSS | Probar desde fuera, o usar la URL local |
| `ERROR: id: duplicado` en fuente-alta | La fuente ya existe | Verificar con `fuente-detalle`; para actualizaciones usar `vigencia-registrar` o editar campos opcionales |
| Alta de fuente se pierde | ~~Carrera de escritores~~ CERRADO (ADR-015): lock flock en todo escritor de la CLI; ver `docs/adr/ADR-015-lock-catalogo.md` | Igual aplicable: un proceso externo que escriba el catálogo fuera de `bloque_catalogo` evade el lock |
| Tailscale `offline` en red IMSS | Relays DERP bloqueados por el firewall | Limitación documentada (R3). Funciona fuera de la red IMSS |
| xlsb "sin estructura" | Formato binario sin lector | Convertir con LibreOffice headless (ver contenedor debian; patrón en docs/ronda-adversarial-2026-09-03.md) y registrar el derivado |
| IP de la Mac cambia y el agente no conecta | DHCP por red | Usar nombres: `1nf0541ud.orb.local` (Mac), `api.halt-to-safe.dev` (público), o Tailscale `*.ts.net` |
| `/archivo` responde 409 | Integridad alterada: sha256 vivo ≠ registrado | Re-ejecutar `vigencia-verificar`; si persiste, auditar el archivo |
| Contenedor en crash-loop al arrancar OrbStack | Puerto 8081 ocupado por instancia host | `pkill -f 'infosalud servir'` y `docker compose up -d` |

## 4. Reglas operativas duras

- **Lock de catálogo (ADR-015)**: toda escritura de la CLI pasa por
  `bloque_catalogo` (flock); altas manuales y lotes pueden convivir.
  Un proceso externo que escriba fuera de `bloque_catalogo` evade
  el lock.
- **Servidor único del puerto 8081**: contenedor O host, nunca ambos.
- **Red IMSS**: no forzar egreso de túneles (riesgo de ban); servir
  solo local/intranet.
- El catálogo se recarga por petición: los cambios en
  `data/fuentes.json` se sirven sin reiniciar el servicio.
- Tras un cambio de estructura del portal, correr
  `auditoria-estructura <id>`: diff contra la verificación previa
  e informe versionado en `data/auditorias/` (ADR-014; `/healthz`
  expone el conteo `auditorias_requieren_revision`).
- Toda verificación de vigencia es la única fuente del estado
  "vigente/cambiada/inaccesible"; nunca inferir por nombre de archivo.

## Sondeo quincenal del portal (PREGUNTA-1 resuelta, 2026-10-08)

Autorizado por el operador: consulta automatizada y periódica del
portal cada 15 días. Implementación operativa (no es código del
servicio; ADR-004 intacto):

- **Script**: `scripts/sondear_portal.py` — GET de sólo lectura a
  las páginas índice (cuumsp2026, ifu_2026, poblacion2026), extrae
  enlaces a archivos y compara contra `data/fuentes.json`. Nunca
  muta el catálogo ni descarga binarios. Salida: informe en
  `data/sondeos/<fecha>.json`; código 3 si hay ediciones nuevas,
  0 si todo está registrado.
- **Agenda**: launchd `com.infosalud.sondeo` (plist en
  `scripts/`, instalado en `~/Library/LaunchAgents`): días 1 y 15
  a las 09:00, log en `data/sondeos/launchd.log`.
- **Flujo tras un sondeo con novedades**: alta con `fuente-alta`
  (hijas de la página índice correspondiente) → descarga y
  `vigencia-registrar` → perfil (lote CUUMSP / generadores) →
  diccionario → si es un corte CUUMSP, re-correr
  `scripts/generar_dimension_unidades.py` (F2 del ADR-016) y
  actualizar `data/cobertura-unidades.json` con la edición vigente.
- **Replicar en otro host**: copiar el plist, ajustar las rutas
  absolutas y `launchctl load ~/Library/LaunchAgents/
  com.infosalud.sondeo.plist`.
