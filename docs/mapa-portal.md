# Mapa del portal Infosalud (declarado por el humano, 2026-09-01)

Estructura de rubros del portal (http://infosalud.imss.gob.mx:8080/).
Fuente: navegación del humano. Los números indican archivos observados
en el momento del levantamiento; cada rubro con "lista histórica"
publica cada actualización como archivo nuevo (ver ADR-012: tomar la
última ingresada salvo pedido expreso).

| Rubro | Contenido | Listado histórico |
|---|---|---|
| Estadísticas Nacionales | Cifras nacionales por año, Día típico, Motivos de consulta, etc. (2) | sí |
| Censos | Censales por padecimiento: DM, HTA, EPOC, ASMA, SM, Oncológico, Eval. Nutricional, etc. (3) | sí |
| Consulta Externa | Atenciones: Especialidades, Med. Familiar, Urgencias, Dental, Paramédicas, etc. (3) | sí |
| Hospital | Egresos, Intervenciones Qx, Partos, Cesáreas, UCI, Complementaria, Subrrogados | sí |
| Defunciones | Defunciones por unidad de atención y adscripción 2004-2025 | sí |
| Recursos (Apoyo) | Infraestructura física: IFU, CUUMSP; indicador de personal (2) | sí |
| Población | PAU, PAMF, Usuaria, etc. (1) | sí |
| Catálogos para los SIS | Catálogos oficiales: Unidades, CIE10, Especialidades, CIE9, Semanas, etc. (7) | sí — piloto v1 (ADR-005) |
| Documentos Normativos y SIS | Marco legal, normas, instructivos, manuales, procedimientos, guías (2) | documentos |
| Sitios de Interés | Enlaces a sitios y aplicaciones institucionales | enlaces |
| Seguimiento Diario/Semanal/Mensual | Reportes y tableros de productividad | sí — alta frecuencia |
| Capacitación | Material de capacitación para personal de SIS | documentos |
| Oficios/Circulares | Oficios y circulares de la División de IS | documentos |
| Validación de Información | Herramientas y lineamientos de validación | documentos |

## Restricción técnica observada (2026-09-01)

El servidor entrega archivos por ruta exacta (GET directo funciona),
pero bloquea el listado de directorios y la raíz con 403 — incluso
con User-Agent de navegador. Las páginas de listado histórico son la
interfaz humana; para que `url_listado` (ADR-012) funcione contra el
portal se requiere: (a) la URL exacta de cada página de listado y
probar si responde 200 al cliente del sistema, o (b) un mecanismo
alterno (página guardada localmente, o feed oficial de DIS) si el
403 es generalizado. Los archivos individuales ya se descargan sin
problema (23/23 fuentes vigente).
