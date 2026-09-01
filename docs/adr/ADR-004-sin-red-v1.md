# ADR-004: La herramienta no hace red en la v1

Estado: aceptado (implementación no iniciada)
Fecha: 2026-09-01

Contexto: D1 y D2 (v1 manual + registro; fail-closed ante la
exposición real del portal, PREGUNTA-2 abierta), y PREGUNTA-1 sin
autorización institucional todavía. REQ-3 exige verificar vigencia,
pero el modo de obtención del archivo era la decisión pendiente.

Decisión: ningún componente de la v1 inicia comunicación de red. El
humano descarga o copia cada archivo por su medio habitual
(navegador en la intranet) y la herramienta registra la evidencia:
huella sha256, fecha y ruta local.

Alternativas descartadas:
  - Descarga dirigida por la herramienta (HTTP plano: el portal no
    ofrece TLS, EV-11): reduce fricción, pero (a) sin autorización
    de frecuencia (PREGUNTA-1) es indebido, y (b) el tráfico plano
    es observable; fail-closed manda.
  - Sondeo programado (cron/launchd): automatización que REQ-6
    reserva para el futuro y que D1 excluye de la v1.

Consecuencias: gana cumplimiento de D1/D2 sin ambigüedad y una
superficie de seguridad mínima (cero sockets). Pierde frescura: la
vigencia se verifica sólo cuando el humano lo hace. Cuando exista
autorización documentada (PREGUNTA-1 resuelta a favor), un ADR nuevo
introducirá la descarga con frecuencia límite declarada. Queda
prohibido cualquier import de librería de red en la v1 (coherente
con ADR-001).
