# Glosario — términos institucionales y del sistema

## Institucionales (IMSS / DIS / DPM)

| Término | Significado |
|---|---|
| **DIS** | División de Información en Salud (opera el portal Infosalud) |
| **DPM** | Dirección de Prestaciones Médicas |
| **UPIS** | Unidad de Planeación e Innovación en Salud |
| **CIIS/CPIM** | Coordinación de Información e Inteligencia en Salud |
| **Infosalud** | Portal oficial de la DIS; origen de todas las fuentes del catálogo |
| **IFU** | Infraestructura Física Usada — censo de infraestructura y equipamiento de unidades médicas; publicación mensual/anual (xlsb en el portal) |
| **CUUMSP** | Catálogo Único de Unidades Médicas en Servicio — identidad de unidades con corte mensual; hojas incluyen Unidad Médica, Unidad y UMAA, Cat_reg_2021 (región↔delegación), Diccionario, Histórico |
| **OOAD** | Órgano de Operación Administrativa Desconcentrada (delegación estatal) |
| **UMAE** | Unidad Médica de Alta Especialidad (hospital de 3er nivel) |
| **UMF / UMF-URPA** | Unidad de Medicina Familiar (URPA: de acceso restringido) |
| **HGZ / HGR / HGZMF** | Hospital General de Zona / con Reserva / HGZ con Medicina Familiar |
| **UAMF** | Unidad Auxiliar de Medicina Familiar |
| **PAMF** | Población Adscrita a Médico Familiar (denominador 1N; corte junio) |
| **PAU** | Población Adscrita a la Unidad |
| **CLUES** | Clave Única de Establecimientos de Salud (identificador federal) |
| **1N / 2N / 3N** | Primer, segundo y tercer nivel de atención |
| **CIE-10 / CIE-9MC / CIE-11** | Clasificaciones internacionales de enfermedades y procedimientos |
| **SIAIS** | Sistema de Información de Atención Integral a la Salud (productividad 1N/2N/3N) |
| **SIMO / SIMOC** | Sistema institucional de productividad médica (tableros DPM) |
| **SIMF** | Sistema Institucional Médico Familiar (captura 1N) |
| **MOCE** | Módulo Oficial de Captura de Estadística |
| **SUI** | Sistema de información de unidades de hospitalización (egresos) — referencial |
| **EPI/IM** | Informe Mensual de Vigilancia Epidemiológica |
| **IDS / MMIM** | Indicadores De Servicios / Indicadores Médicos MMIM (tableros) |
| **SIS** | Sistemas de Información en Salud (genérico) |
| **DCAI / DAD** | Fechas de disponibilidad / asesores de validación (calendarios institucionales) |

## Del sistema (Infosalud Nexus)

| Término | Significado |
|---|---|
| **Fuente** | Registro del catálogo: url + formato + verificaciones (esquema cerrado) |
| **Verificación** | Descarga/registro con fecha, huella sha256, resultado (vigente/cambiada/inaccesible), ruta local, estructura |
| **Huella** | sha256 del archivo verificado; sirve como ETag y versión |
| **url_listado** | Página de listado histórico; ADR-012 toma la última ingresada |
| **parent_source_id / aliases / corte_declarado** | Campos de preservación (enmienda 2026-09-03): origen índice, alias de búsqueda, periodo declarado |
| **Diccionario** | `data/diccionarios/<id>.json`: campos observados de una fuente (ADR-009) |
| **Borrador asistido** | Generación de diccionario desde el archivo local verificado (ADR-010) |
| **Exportación** | CSV/SQLite con evidencia de origen (ADR-011) |
| **Conciliación numérica** | Σ(detalles) ≈ total declarado, con tolerancia; advisory: califica el dato sin bloquearlo (ADR-014) |
| **Auditoría nivel 1** | Diff estructural automático entre verificaciones; informe versionado con huella propia |
| **Perfil estructural** | (ADR-014, v1) contrato por hoja: encabezados (y sub), rango de datos, totales, notas, segmentos multi-bloque y conciliaciones |
| **Dimensiones** | Clave → atributos canónicos (servicio, subdelegación) derivadas de catálogos verificados y servidas en `/dimensiones/{nombre}` |
| **FN-19 / FN-20** | Indicador de demanda (casos/población×1000) y demanda esperada (CEPI) |
| **Sondeo** | Verificación automática programada vía launchd (ADR-008) |
| **Túnel / halt-to-safe.dev** | Exposición pública vía Cloudflare (rutas policy-routing por WiFi) |
| **AN-KLA** | Memoria de sesión versionada (checkpoints, facts, lecciones) |
| **Skevi** | Metodología de desarrollo usada por el proyecto (F0→F3, contratos, ADRs) |