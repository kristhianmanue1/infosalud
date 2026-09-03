# Entrega: preservación y consulta — IFU, CUUMSP y Regionalización
# (retro consumidor CEPI, 2026-09-03)

Modo: consulta, incorporación y preservación. Sin reglas de negocio
de consumidores, sin exportar, sin modificar originales, sin
sobrescribir fuentes. Estados de consumidor ("apto para CEPI",
"validado por CTIM") NO agregados — cada consumidor evalúa en su
ámbito (punto 9 cumplido).

## 1. Fuentes nuevas incorporadas (14, todas vigente)

Hijas de la página índice `recursos-ifu-2026` (parent_source_id):

| id | corte_declarado | formato | huella (prefijo) |
|---|---|---|---|
| recursos-ifu-nacional-enero-2026 | enero 2026 | xlsb (otro) | f019ccf787d7 |
| recursos-ifu-nacional-febrero-2026 | febrero 2026 | xlsb | da813b2eae2e |
| recursos-ifu-nacional-marzo-2026 | marzo 2026 | xlsb | 47f63c423672 |
| recursos-ifu-nacional-abril-2026 | abril 2026 | xlsb | 80e7a7c05424 |
| recursos-ifu-nacional-mayo-2026 | mayo 2026 | xlsb | 21b1a796bc3d |
| recursos-ifu-nacional-junio-2026 | junio 2026 | xlsb | 427312c306ca |
| recursos-ifu-documento-2b52-b03-004 | sin determinar | pdf | 2a98f70d790c |

Hijas de la página índice `recursos-cuumsp-2026`:

| id | corte_declarado | formato | huella (prefijo) |
|---|---|---|---|
| recursos-cuumsp-enero-2026 | enero 2026 | xlsx | 46eb4b7966f4 |
| recursos-cuumsp-febrero-2026 | febrero 2026 | xlsx | ef0a2bfe2475 |
| recursos-cuumsp-marzo-2026 | marzo 2026 | xlsx | 701e860eff7c |
| recursos-cuumsp-abril-2026 | abril 2026 | xlsx | 035ab00e4fcd |
| recursos-cuumsp-mayo-2026 | mayo 2026 | xlsx | 931f1f68c653 |
| recursos-cuumsp-junio-2026 | junio 2026 | xlsx | d38c4f559efe |
| recursos-cuumsp-julio-2026 | julio 2026 | xlsx | 23299eede88f |

Previamente registradas (ya existían, se enriquecieron con
aliases/parent): recursos-ifu-nacional-julio-2026,
recursos-ifu-nacional-diciembre-2025, recursos-cuumsp-2026-agosto,
recursos-cuumsp-diciembre-2025, y las 2 páginas índice.
Catálogo total: 70 fuentes, todas con archivo descargado y huella.

## 2. Relación índice → archivos hijos

Campo nuevo `parent_source_id` (contrato registro-de-fuente v1,
opcional, compatible): cada hijo declara su página índice. Alias de
búsqueda incorporado vía campo `aliases` (también sirve en
`fuente-buscar` y en el API/MCP). Alias generales aplicados:
"IFU", "Infraestructura Física Usada", "CUUMSP", "Catálogo Único de
Unidades Médicas", más el mes/año de cada corte.

## 3. IFU dic-2025 (derivado xlsx): hojas identificadas

13 hojas: Unidad, OOAD_UMAE, Region, 50100 Camas Censables,
60000 Camas No Censables, 71200 Especialidades, Quirófanos,
Equipamiento, IFU- BAJAS Y CAMBIOS, IFU- Solicitudes, Normativas,
Metodología, Equivalencias.

**Unidad: presente. Metodología: presente.** Sin interpretación de
campos (punto 5). Los xlsb mensuales aún no son legibles (ver §7).

## 4. CUUMSP agosto 2026: campos disponibles (40 columnas,
hoja "Unidad Médica", encabezados en fila 10)

- Identificación: Región 2021, CLUES Salud, Clave Personal,
  Unidad de Información PREI, Clave Ubicación Admin, Clave
  Presupuestal, Clave Delegación o UMAE, Nombre Delegación o UMAE,
  Relación Delegación-UMAE, Unidad Presupuestal, Número de Unidad,
  Denominación Unidad, Nombre Unidad.
- Clasificación: Nivel de Atención, Tipo de Servicio, Descripción
  Tipo Servicio.
- Domicilio: Dirección, Tipo/Nombre de Vialidad, Entre Vialidades,
  Número Exterior, Tipo/Nombre de Asentamiento, Código postal,
  Clave/Nombre Municipio, Clave/Nombre Localidad, Clave/Nombre
  Entidad Federativa, Clave/Nombre Jurisdicción Sanitaria,
  LATITUD, LONGITUD.
- **Fechas**: Inicio de Productividad, Licencia de Funcionamiento,
  Aviso de Funcionamiento, Fecha de Construcción.
- **Situación/estatus**: NO existe columna explícita de "estatus de
  operación". Lo más cercano: Licencia/Aviso de Funcionamiento
  (contenido no examinado). **No se infiere que ninguno certifique
  operación** (punto 6).
- Otras hojas: Indice, Anexos COVID, Total Unidades x Del,
  Total Unidades x tipo, Detalle UAMF, Total UAMF, **Diccionari**
  (diccionario de datos embebido en el propio archivo),
  **Control de Cambios** (2015-2023), **Histórico**,
  **Cat_reg_2021**.

## 5. Regionalización

- **Localizada dentro del CUUMSP**: hoja `Cat_reg_2021` = tabla
  región ↔ delegación (CVE_DEL, CVE_REG, Nom_Región, Antes,
  Nom_Del); cada unidad en "Unidad Médica" trae "Región 2021" y
  "Clave/Nombre Delegación o UMAE"; "Relación Delegación-UMAE"
  es la relación explícita delegación→UMAE.
- **No localizada**: la relación primer nivel → hospital/red de
  referencia como archivo independiente en el portal (no aparece en
  los 11 fragmentos ni en las páginas índice revisadas). La clave
  CLUES + "Relación Delegación-UMAE" es lo más cercano disponible.
- Fuente dedicada de Regionalización de servicios: **no encontrada
  en el portal** (buscado en los 11 fragmentos de navegación).

## 6. Estados separados (mapeo a campos reales)

| Estado pedido | Dónde vive |
|---|---|
| archivo localizado | fuente registrada con url |
| archivo descargado | verificación con ruta_local (y `/cobertura`.descargado) |
| integridad verificada | huella + recomputo vivo en `/archivo/meta` |
| vigencia reportada por la fuente | verificaciones[].resultado (solo tras verificación real; **nunca por nombre de archivo**) |
| estructura identificada | verificaciones[].estructura (xlsx únicamente; xlsb/pdf sin estructura) |
| evaluación semántica | `estado_semantico: sin_evaluar` (pendiente; no hay auditorías aún) |

## 7. Posibles duplicados detectados

- `recursos-cuumsp-2026-agosto` (ya registrado) vs
  `recursos-cuumsp-agosto-2026` (generado por esta entrega): mismo
  archivo, ids distintos por convención de nombre. **Resuelto**: se
  excluyó el nuevo; prevalece el existente. Pendiente de normalizar
  la convención de ids en un futuro commit.
- Sin duplicados de contenido: cada huella es única en el catálogo.

## 8. No recuperables y causa

- IFU meses 2026 (xlsb): descargados ✅ pero **sin estructura**
  extraíble hasta contar con lector/conversor para los meses
  restantes (dic-2025 ya convertido como derivado).
- Regionalización dedicada (red primer nivel → hospital): no
  localizada en el portal (punto 5 de este documento).
- Tableros IFU/CUUMSP en Tableau: existen pero no descargables
  como archivo (requieren sesión/interfaz).

## 9. Limitaciones de interpretación pendientes

1. Perfiles estructurales por hoja (ADR-014 propuesto): sin ellos,
   `fila_encabezados` y rangos no están formalizados.
2. Semántica de campos CUUMSP (¿"Relación Delegación-UMAE" qué
   certifica?) — requiere área.
3. Estatus de operación de unidades: campo no identificado sin
   inferir; si el CEPI lo necesita, pedirlo a la DIS.
4. Contenido del PDF 2B52-B03-004: no examinado (preservado).
5. Interceptación TLS (Fortinet) en red IMSS: probar el acceso
   público desde la intranet.