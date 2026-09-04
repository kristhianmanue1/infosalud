# Diagramas del sistema (mermaid — renderizan en GitHub)

## 1. Arquitectura lógica

```mermaid
flowchart LR
    P[Portal Infosalud<br/>origen oficial] -->|GET xlsb/xlsx<br/>solo vigencia-verificar| S[Servicio infosalud<br/>API JSON + MCP]
    S --> C[(data/fuentes.json<br/>70 fuentes + huellas)]
    S --> D[(data/diccionarios)]
    S --> X[data/exportaciones<br/>CSV/SQLite]
    A1[Agente CEPI<br/>http/MCP] --> S
    A2[Agentes internos<br/>intranet] --> S
    L[sondeo launchd<br/>mensual] -->|vigencia-verificar| P
    L --> C
```

## 2. Topología de red y exposición

```mermaid
flowchart TB
    subgraph Mac mini [Mac mini M1 - dual red]
      direction TB
      CONT[contenedor 1nf0541ud<br/>:8081 restart always]
      HOST[servicio host<br/>respaldo :8081]
      CF[cloudflared<br/>LaunchAgent http2]
      TS[tailscaled userspace<br/>LaunchAgent]
      R[rutas policy-routing<br/>LaunchDaemon root cada 60s]
    end
    subgraph Intranet IMSS [en0 - 172.25.0.115]
      I[consumidores internos]
      PO[Portal Infosalud]
      FW[Fortinet: filtra egreso<br/>7844 y relays]
    end
    subgraph Internet [en1 - WiFi/hogar]
      E[agentes externos]
      CFE[Edge Cloudflare]
      DRP[DERP Tailscale]
    end
    CONT -->|publica 8081| CF
    I -->|http 172.25.0.115:8081| CONT
    E -->|https api.halt-to-safe.dev| CFE -->|túnel http2| CF
    E -.->|ts.net offline en IMSS| DRP -.-> TS
    R -->|rutas edge via en1| CF
    PO -.->|solo red IMSS| FW
```

## 3. Flujo de datos: del portal al consumidor

```mermaid
sequenceDiagram
    participant H as Humano/agente
    participant S as Servicio (API/MCP)
    participant P as Portal Infosalud
    participant C as Catálogo (fuentes.json)
    H->>S: fuente-alta (url, parent, aliases, corte)
    S->>C: registra (valida contrato, parent existe)
    H->>S: vigencia-verificar <id>
    S->>P: GET archivo (read-only, timeout, tope)
    S->>C: verificación (fecha, huella sha256, estructura)
    H->>S: fuente-campos --borrador
    S->>S: diccionario desde estructura observada
    H->>S: fuente-exportar (CSV/SQLite)
    S->>H: productos + evidencia (ADR-011)
    H->>S: GET /fuentes/{id}/archivo/meta
    S-->>H: envelope (sha256 recomputado en vivo)
    H->>S: perfil v1 (data/perfiles/<id>.json)
    S->>S: valida contrato perfil-de-fuente v1
    H->>S: GET /fuentes/{id}/datos (nivel 2)
    S-->>H: datos segmentados + conciliación + ETag compuesto
    H->>S: GET /dimensiones/{nombre}
    S-->>H: clave → atributos (derivada de catálogo verificado)
```

## 4. Máquina de estados: vigencia de una fuente

```mermaid
stateDiagram-v2
    [*] --> desconocida: alta
    desconocida --> vigente: verificación exitosa
    vigente --> vigente: huella igual
    vigente --> cambiada: huella distinta (url_previa)
    cambiada --> vigente: verificación de la nueva
    cualquier --> inaccesible: red/contenido/corrupto
    inaccesible --> vigente: verificación exitosa
```
