# Despliegue público — halt-to-safe.dev (plataforma multi-proyecto)

Fecha: 2026-09-03. Dominio del área para servicios de agentes.
Registrado en suempresa.com, DNS gestionado por Cloudflare
(nameservers joan/tate.ns.cloudflare.com, DNSSEC off).

## Arquitectura

- **Túnel**: `halt-to-safe` (id d5f2e82c-dbd2-48f4-9c62-5a6694789492),
  modo LOCAL: el ingress vive en `deploy/cloudflared-config.yml`
  (espejo de ~/.cloudflared/config.yml) — versionado, reproducible.
- **Convención**: un subdominio por proyecto → un puerto local.
  Agregar proyecto = bloque hostname/service en el config.yml +
  `cloudflared tunnel route dns -f halt-to-safe <sub>.halt-to-safe.dev`.
- **Conector**: LaunchAgent `com.infosalud.cloudflared`
  (~/Library/LaunchAgents, KeepAlive) → `cloudflared tunnel run`.
- **Fail-closed**: todo host no declarado → 404.

## Subdominios activos

| Subdominio | Proyecto | Puerto | |
|---|---|---|---|
| infosalud.halt-to-safe.dev | Infosalud Nexus (API+MCP) | 8081 | ✅ |
| api.halt-to-safe.dev | alias → Infosalud | 8081 | ✅ |

## Cadena de arranque automático

login → OrbStack (start_at_login) → contenedor 1nf0541ud
(restart:always, puerto 8081) + servicio host de respaldo →
cloudflared (KeepAlive) → https://… público.

## URL públicas (verificadas 2026-09-03)

- https://infosalud.halt-to-safe.dev/healthz → 50 fuentes vigente
- https://api.halt-to-safe.dev/fuentes/{id}/archivo/meta → integridad OK
- https://api.halt-to-safe.dev/mcp → 10 herramientas MCP
