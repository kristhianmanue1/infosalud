# ADR-013: Servicio de lectura para agentes — HTTP JSON + MCP
# (stdlib), v2/REQ-5

Estado: aceptado (implementación en esta misma rama)
Fecha: 2026-09-02

Contexto: el consumidor primario del sistema son agentes de IA
(ADR-006), pero la única interfaz es la CLI local: un agente en otra
máquina de la intranet no puede consultar el catálogo, la vigencia
(huellas, fechas, url_previa), los diccionarios ni las exportaciones
sin acceder al repositorio. REQ-5 (servir a sistemas) quedó en
horizonte desde F0. La frontera de ADR-004 ("la v1 no abre
sockets") cumple su ciclo; esta decisión la supera explícitamente
para v2, igual que ADR-008 superó la prohibición de red para
`vigencia-verificar`.

Decisión:
1. Nuevo módulo `infosalud/servicio.py` y subcomando
   `python3 -m infosalud servir`: servidor HTTP de SÓLO LECTURA
   (stdlib `http.server`), con:
   - API JSON: `GET /`, `/healthz`, `/fuentes`, `/fuentes/{id}`,
     `/fuentes/{id}/campos`, `/fuentes/{id}/historia`,
     `/fuentes/{id}/exportar?formato=csv|sqlite`.
   - Capa MCP (JSON-RPC 2.0 sobre `POST /mcp`, transporte Streamable
     HTTP en modo sin sesión): `initialize`, `tools/list`,
     `tools/call` con tools `mapa_servicio`, `buscar_fuentes`,
     `detalle_fuente`, `diccionario_fuente`, `historia_fuente`,
     `exportar_fuente`.
2. Sólo stdlib (ADR-001): el servidor NO depende del SDK de MCP; el
   protocolo expuesto es JSON-RPC 2.0 con la superficie mínima del
   spec (initialize/tools). Si el spec deriva hacia requisitos que
   stdlib no cubre, se reevalúa con ADR nuevo (la Opción B, SDK
   oficial, fue descartada por la regla de dependencias).
3. El servicio es pasarela de lectura: no descarga del portal, no
   muta el catálogo, no calcula vigencia. Toda frescura sigue
   perteneciendo al ciclo `vigencia-verificar` + sondeo launchd
   (ADR-008); el servicio sólo lee el estado en disco (falla si el
   catálogo es inválido: fail-closed de `cargar_catalogo`).
4. Superficie de seguridad mínima: bind por defecto a `127.0.0.1`
   (configurable para la intranet), token opcional por variable de
   entorno (`INFOSALUD_SERVICIO_TOKEN`, nunca en argv ni logs),
   métodos GET/POST únicamente, sin navegación de rutas del
   filesystem, `fuente-exportar` escribe a directorio temporal por
   petición y se entrega como zip en memoria.
5. Contrato nuevo `servicio-infosalud v1` (docs/f1-contratos.md) y
   SPEC-9 (docs/f1-specs.md); tests DADO/CUANDO/ENTONCES en
   `tests/test_servicio.py` con servidor en puerto efímero.
   Despliegue con el patrón launchd existente (docs/sondeo-launchd.md).

Alternativas descartadas:
  - SDK oficial de MCP (dependencia externa): primera dependencia
    fuera de stdlib; sin ADR que la justifique hoy.
  - Snapshot JSON estático: cubre el mapa pero no consultas por id
    ni filtros; los agentes tendrían que bajar todo.
  - Exponer el repo por SMB/git: los consumidores tendrían que
    instalar y entender la CLI; duplicaría la lógica de vigencia.
  - Reutilizar el puerto/infraestructura del portal: jamás; el
    servicio es local a la DPM y de sólo lectura.

Consecuencias: gana consumo mecanizado por agentes remotos con
descubrimiento de herramientas (MCP) y JSON estable (contrato);
los archivos y el catálogo nunca salen del perímetro salvo como
productos derivados ya verificados (exportación ADR-011). Pierde
simplicidad operativa: un puerto que abrir en la intranet (minimiza
por bind por defecto y token opcional) y una superficie MCP que
mantener ante evoluciones del spec (mitigado: sólo
initialize/tools, sin sesiones ni SSE).
