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

## Actualización (2026-09-02): el puerto 80 sí expone la navegación

La raíz **sin puerto** (`http://infosalud.imss.gob.mx/`, puerto 80)
responde 200 con el portal completo (v2.4); el 403 es sólo de la
raíz `:8080`. Las "ventanas de contexto" del menú son modales
Bootstrap (`#modalSeccion-1..11`) cuyo contenido se carga por AJAX
desde **`/fragmentos/seccion/<N>`**, y cada fragmento trae los
enlaces directos a archivos `:8080/ARCHIVOS/...` (varios bajo
`/uploads/archivos/<id>/` con nombre fechado). Fragmentos observados
y su contenido (títulos según contenido, no según orden del menú):

| Fragmento | Contenido observado (enlaces directos) |
|---|---|
| /fragmentos/seccion/1 | Cifras Nacionales 2019–2026 (xlsx; 2026 julio preliminar), Día Típico 2023–2026 (aspx), histórico 2016-2022, Efemérides, IDS Dashboard, Datos Abiertos, Memoria Estadística |
| /fragmentos/seccion/2 | Consulta Externa: series homologadas 2012–2024 (Especialidades, Urgencias, Med Fam, Dental), Horas trabajadas 2/3N, SIAIS Parte Uno fin de semana y paramédicos (zip), enlaces IDS |
| /fragmentos/seccion/3 | Hospital: Egresos 2012–2024 (OOAD-UMAE y por unidad, xlsb), Intervenciones Qx, Partos y Cesáreas 2026 (analítica), Nacidos Vivos, UCI 2016–2026, Subrogados (tablero `SUBROGADOS_DataMart`), Indicadores de Calidad |
| /fragmentos/seccion/4 | Defunciones: Unidad de Atención y de Adscripción 2004–2024 (xlsb) |
| /fragmentos/seccion/5 | Censos: páginas por año censoYYYY.htm (DM/EPOC/tumores malignos/etc. 2011–2025), Censo Oncológico (aspx) |
| /fragmentos/seccion/6 | Recursos: IFU por año `paginas/ifu_YYYY.html` 2012–2026, CUUMSP `paginas/cuumspYYYY.html` 2021–2026 |
| /fragmentos/seccion/7 | Población: PAMF SIAIS 2007–2025 (corte junio), Total Consultorios MedFam PAMF 2018–2025, Población usuaria 1N por unidad/OOAD 2004–2025, usuaria 2N/3N SIMOC por unidad 2017–2025, páginas poblacionYYYY |
| /fragmentos/seccion/8 | Catálogos SIS: los ya registrados + Buscador CIE-11, Catálogo Unidades Acceder 2020, semanas 2019–2025, CPxUMF |
| /fragmentos/seccion/9 | Documentos Normativos y sistemas: ECE, comunidades SIMF/SIMO, PHEDS (urgencias/hospitalización y prog. qx), RLC-SIAIS nacional, CPIM, Tableros de Gestión DPM, MMIM (intranet), DCAI/DAD |
| /fragmentos/seccion/10 | Sitios/Capacitación: documentación CEMECE, auxiliares de codificación |
| /fragmentos/seccion/11 | Seguimiento D/S/M: tablero CifrasGenerales/IFU, productividad semanal xlsx (semana 52 cortes 2023/2024/2025), rankings semanales y acumulados OOAD/UMAE (PDF), Metas 2023, monitoreo SIAIS/SIMOC, IFU Tablero Estadístico y Seguimiento de Solicitudes, INDOQ, cédulas CSIC OOAD/UMAE, Indicadores CVE 02/03 (MMIM) |

Nota: los enlaces `/uploads/archivos/<id>/...` usan nombre fechado
(variante por actualización), igual que las series SIAIS ya
registradas. El índice para `url_listado` por fuente puede ser el
propio fragmento del portal (host distinto, puerto 80) o una página
dedicada; pendiente validar el parser de ADR-012 contra fragmentos.

Fuentes registradas a partir de este hallazgo (2026-09-02): PAMF
2025, Total Consultorios MedFam PAMF 2025, población usuaria 1N
unidad 2004-2025, usuaria 2N/3N SIMOC 2025, productividad semanal
semana 52/2025 y Cifras Nacionales 2025 (catálogo pasa de 23 a 29).

## Validación del parser `url_listado` contra fragmentos (2026-09-02)

Prueba empírica (en copia del catálogo, sin mutar el real): se
asignó `url_listado=/fragmentos/seccion/7` a `poblacion-pamf-siais-2025`
y se corrió `vigencia-verificar`. Resultado:

- **Mecánicamente funcional**: el parser encontró 39 enlaces a
  archivos en el fragmento; la comparación de host es por hostname
  (sin puerto), así que los enlaces `:8080` dentro de un fragmento
  del puerto 80 califican; la heurística de fechas leyó los nombres
  fechados (`_24082026…`, `_2026-02-24`).
- **Inseguro con fragmentos multi-producto**: eligió
  `PDA_DPM260731_24082026114154.xlsx` ("Reporte DIR 2004–2026"),
  un producto DISTINTO del mismo fragmento con fecha más nueva, y
  reportó un falso `cambiada` reemplazando la `url` del PAMF.
  "La última ingresada del fragmento" ≠ "la última del producto".
- **Ciego a páginas índice html**: `EXTENSIONES_LISTADO` no incluye
  `.html`, así que las páginas anuales de IFU/CUUMSP (`paginas/…`)
  nunca serían seleccionadas como "nueva versión".

Conclusión: NO usar fragmentos como `url_listado` de fuentes
individuales en el estado actual. Caminos posibles (ADR-013
potencial, requiere decisión): (a) páginas de listado dedicadas por
producto si el portal las ofrece; (b) extender el parser con
acotamiento por producto (similitud de ruta/texto contra la `url`
registrada); (c) ampliar `EXTENSIONES_LISTADO` para índices html.
Mientras tanto, las series se vigilan por URL fija (comportamiento
ADR-012 sin `url_listado`).

Series de casos registradas y vigentes (2026-09-02, catálogo 29→38):
consulta externa homologada 2012-2024 (especialidades, urgencias,
medicina familiar, dental), egresos 2012-2024 por OOAD-UMAE (hoja
por año: "Egresos por OOAD y UMAE, según mes, tipo de ingreso y
sexo") y por unidad médica (xlsb, formato "otro"), intervenciones
Qx 2019-2024, UCI 2016-2024 e IFU 2026 (página índice html).
Diccionarios borrador generados para los 7 xlsx.
