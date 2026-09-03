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
| Alta de fuente se pierde | Carrera de escritores: alta concurrente con lote vigencia-verificar (P13) | Regla: nunca alta manual + lote en paralelo. Pendiente ADR-015 (flock) |
| Tailscale `offline` en red IMSS | Relays DERP bloqueados por el firewall | Limitación documentada (R3). Funciona fuera de la red IMSS |
| xlsb "sin estructura" | Formato binario sin lector | Convertir con LibreOffice headless (ver contenedor debian; patrón en docs/ronda-adversarial-2026-09-03.md) y registrar el derivado |
| IP de la Mac cambia y el agente no conecta | DHCP por red | Usar nombres: `1nf0541ud.orb.local` (Mac), `api.halt-to-safe.dev` (público), o Tailscale `*.ts.net` |
| `/archivo` responde 409 | Integridad alterada: sha256 vivo ≠ registrado | Re-ejecutar `vigencia-verificar`; si persiste, auditar el archivo |
| Contenedor en crash-loop al arrancar OrbStack | Puerto 8081 ocupado por instancia host | `pkill -f 'infosalud servir'` y `docker compose up -d` |

## 4. Reglas operativas duras

- **Escritor único del catálogo**: nunca `fuente-alta` manual junto
  a lotes de `vigencia-verificar` en paralelo (carrera documentada:
  ronda adversarial, P13).
- **Servidor único del puerto 8081**: contenedor O host, nunca ambos.
- **Red IMSS**: no forzar egreso de túneles (riesgo de ban); servir
  solo local/intranet.
- El catálogo se recarga por petición: los cambios en
  `data/fuentes.json` se sirven sin reiniciar el servicio.
- Toda verificación de vigencia es la única fuente del estado
  "vigente/cambiada/inaccesible"; nunca inferir por nombre de archivo.
