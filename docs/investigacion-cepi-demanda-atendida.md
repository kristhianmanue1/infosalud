# Investigación (sólo lectura): fuente para "Demanda Atendida
# y Demanda Esperada" de CEPI Médica (FN-19 / FN-20)

Fecha: 2026-09-02. Ejecutor: agente Cline, modo sólo lectura.
Alcance: identificar y falsar candidatos que alimenten FN-19
(Casos OOAD/UMAE ÷ Población OOAD/UMAE × 1,000) y FN-20
(Población Zona de Influencia × Indicador ÷ 1,000), con
evidencia verificable. Sin modificar sistemas, catálogos,
permisos ni datos; sin información nominal; sin secretos.

Método: inventario completo del catálogo local
(`data/fuentes.json`, 23 registros), 19 diccionarios
(`data/diccionarios/`), documentación canónica (`docs/f0`,
ADR-005, ADR-012, `docs/mapa-portal.md`) y sondas de sólo
lectura al portal (root → HTTP 403, consistente con
`mapa-portal.md`). No hubo acceso a bases internas de SIAIS,
SUI, SIMF ni DataMart: este entorno no las alcanza; todo lo
que dependa de ellas se declara como inferencia o suposición.

## A. SABEMOS (evidencia directa)

- **El catálogo local no contiene ninguna fuente de casos
  agregados.** Las 23 fuentes registradas pertenecen todas a
  la sección `catalogos` (verificado con
  `fuente-lista --json`): catálogos CIE-10/9, listas,
  servicios/especialidades, OOAD, semanas, vacunas, PTDAM.
  Ninguna registra "número de casos" por unidad, servicio ni
  periodo. ⇒ Ningún candidato está hoy *capturado* en el
  sistema, aunque el portal sí publica rubros con esos datos.
- **El portal declara rubros con datos agregados por unidad
  y servicio** (`docs/mapa-portal.md`, declarado por el
  humano; `f0-analisis.md` §3 EV-14): Estadísticas Nacionales
  (2 archivos), Censos (3), Consulta Externa (3), Hospital
  (egresos, Qx, partos, cesáreas, UCI, complementaria,
  subrrogados), Defunciones 2004–2025, Población (PAU, PAMF),
  Seguimiento Diario/Semanal/Mensual. Existen como archivos
  nuevos por actualización (listas históricas, ADR-012), pero
  sus URLs no están registradas y el listado de directorios
  responde 403 (re-verificado 2026-09-02).
- **Claves de unidad y servicio existen y están vigentes**:
  - `catalogo-ooad-subdelegaciones` (xls, corte feb 2025,
    huella `b0d9d26b…`, vigente): relación unidad ↔ OOAD /
    subdelegación. Sin estructura observada (xls binario, no
    parseado por los lectores actuales) ni diccionario.
  - `catalogo-servicios-especialidades-maestro` (xlsx,
    corte 12/05/2026, huella `ff7adb1e…`, hojas
    Catálogo_Maestro_de_Servicios / Solo_Cambios / Variables;
    notas: "insumo directo de MOCE y SIMO").
  - `conversor-servicios-especialidades-simo-moce` (xlsx, jun
    2020, huella `f494a76d…`): equivalencias SIMO / MOCE /
    iCITAS / SIOC — evidencia de que los SIS usan catálogos
    de servicio distintos y que existe tabla oficial de
    correspondencia.
  - `catalogo-maestro-semanas-estadisticas` (huella
    `d77e1260…`): notas "Base de cierres semanales de los
    SIS" ⇒ existe noción oficial de corte semanal definitivo.
- **El repositorio de tableros DPM existe y es alcanzable**:
  `catalogos-simoc-por-unidad-medica` (Tableau,
  `tableros.imss.gob.mx/t/PrestacionesMedicas/views/...`,
  huella `6c33f794…`, vigente; nota: "no descargable como
  archivo"). `f0` EV-14 registra además los tableros Egresos
  Hospitalarios, Día Típico, SIMOC, IDS y MMIM enlazados en
  el portal. ⇒ El candidato F (tableros de DPM/CPIM) existe;
  el tablero no basta como fuente (requisito del encargo) y
  aún no identificamos el sistema detrás de cada vista.
- **Alcance v1**: por ADR-005, la v1 cubre sólo la sección
  "Catálogos para los SIS"; vigencia automática (ADR-008) y
  listados históricos (ADR-012) están operativos y listos
  para incorporar los rubros de estadística cuando existan
  las URLs.
- **SIAIS está presente sólo como catálogos**, no como
  productividad: los 11 registros SIAIS del catálogo son
  catálogos (CIE-10, CIE-9MC, servicios/especialidades 1N,
  acciones, vacunas, PTDAM, nomenclatura de consultorios
  SIMF). Nada de ello prueba que exista una salida agregada
  nacional de productividad SIAIS por unidad/servicio/periodo.

## B. INFERIMOS (relaciones razonables, sin confirmar)

- SIMF es el sistema de primer nivel (el catálogo CIE-10
  SIMF "base para MOCE/SIMF"; nomenclatura de consultorios
  SIMF) ⇒ las consultas de Medicina Familiar y la
  productividad 1N probablemente viven en SIMF/SIMO, y su
  total oficial debería cuadrar con el rubro "Consulta
  Externa" del portal. **Pendiente: confirmar semántica con
  el propietario.**
- Los rubros "Hospital" (egresos, Qx, partos, cesáreas, UCI)
  y "Consulta Externa" del portal son la vía natural para
  obtener casos agregados por unidad/especialidad/año sin
  tocar datos nominales; la existencia del tablero "Egresos
  Hospitalarios" sugiere que hay un total oficial
  conciliable. **Pendiente: descargar y observar estructura.**
- PAMF/PAU (rubro "Población") es el denominador probable de
  FN-19/FN-20; el catálogo de OOAD/subdelegaciones sugiere
  que existe desglose por unidad. **Pendiente: confirmar
  campo, corte y responsable.**
- Los cierres semanales (catálogo de semanas) implican que
  los SIS marcan cortes definitivos semanales/mensuales;
  "definitivo vs preliminar" probablemente se distingue por
  fecha de corte y no por campo explícito en los archivos.

## C. SUPONEMOS (no demostrado)

- Que SIAIS puede producir agregados nacionales 1N/2N/3N por
  unidad, servicio y periodo con claves CUUMSP.
- Que DataMart está dado de baja o tiene sucesor formal.
- Que SUI publica egresos/Qx agregados descargables.
- Que la población PAMF y los casos comparten el mismo corte
  anual (requisito del fail de la prueba mínima).
- Que las sumas por OOAD no duplican registros (p. ej.,
  unidades con doble adscripción o registros compartidos).

## D. Matriz de fuentes

| Rubro | Métrica/casos | Sistema candidato | Tabla/vista | Campo | Unidad de medida | Corte | Clave de unidad | Cobertura | Propietario | Estado de validación |
|---|---|---|---|---|---|---|---|---|---|---|
| Hospitalización | Egresos por especialidad | Rubro "Hospital" del portal / tablero Egresos | archivo xlsx (URL por conocer) | por observar | egresos | anual (por observar) | por observar | nacional (por observar) | DIS/DPM | evidencia insuficiente |
| Consultas especialidades | Consultas otorgadas | Rubro "Consulta Externa" / SIMO | archivo xlsx (URL por conocer) | por observar | consultas | por observar | por observar | nacional (por observar) | DIS/DPM | evidencia insuficiente |
| Cirugía | Intervenciones Qx | Rubro "Hospital" / SIOC | archivo (URL por conocer) | por observar | cirugías | por observar | por observar | por observar | DIS/DPM | evidencia insuficiente |
| Tococirugía | Cesáreas, partos, legrados | Rubro "Hospital" | archivo (URL por conocer) | por observar | procedimientos | por observar | por observar | por observar | DIS/DPM | evidencia insuficiente |
| Urgencias | Atenciones de urgencias | Rubro "Consulta Externa" / SIMO | archivo (URL por conocer) | por observar | atenciones | por observar | por observar | por observar | DIS/DPM | evidencia insuficiente |
| UCI | Ingresos/egresos/días-cama | Rubro "Hospital" | archivo (URL por conocer) | por observar | por observar | por observar | por observar | por observar | DIS/DPM | evidencia insuficiente |
| Imagenología / Laboratorio / Patología / Banco de Sangre | Estudios/procedimientos | Sin candidato capturado | — | — | estudios | — | — | — | por identificar | evidencia insuficiente |
| Diálisis / Quimioterapia / Terapia respiratoria / MFR | Sesiones/procedimientos | Sin candidato capturado | — | — | sesiones | — | — | — | por identificar | evidencia insuficiente |
| Medicina Familiar / Preventiva / Estomatología / Med. Trabajo | Consultas | SIMF / SIMO (inferido) | — | — | consultas | por observar | por observar | 1N (inferido) | por confirmar | evidencia insuficiente |
| Población (denominador) | PAMF / PAU / usuaria | Rubro "Población" del portal | archivo (URL por conocer) | por observar | derechohabientes | por observar (debe coincidir con casos) | `catalogo-ooad-subdelegaciones` (feb 2025) | nacional | por confirmar | evidencia insuficiente |
| Claves de unidad | — | `catalogo-ooad-subdelegaciones` | hoja xls | por observar (xls binario) | — | 2025-02 | clave institucional | nacional | DIS | capturado y vigente; sin diccionario |
| Claves de servicio | — | `catalogo-servicios-especialidades-maestro` + conversor SIMO/MOCE/iCITAS/SIOC | hojas xlsx | por observar | — | 2026-05-12 / 2020-06 | clave de servicio | nacional | DPM/CPIM | capturado y vigente; sin diccionario completo |

## E. Diccionario mínimo (campo CEPI → institucional)

| Campo CEPI | Campo institucional | Definición | Tipo | Unidad | Agregación | Fuente | Periodicidad |
|---|---|---|---|---|---|---|---|
| Unidad (clave) | por confirmar (`catalogo-ooad-subdelegaciones`) | clave institucional de unidad | clave | — | grupo | Infosalud catálogos | eventual (feb 2025) |
| OOAD/UMAE | OOAD (`catalogo-ooad-subdelegaciones`) | órgano de operación administrativa delegacional | clave | — | grupo | Infosalud catálogos | eventual |
| Servicio/especialidad | clave de servicio (`catalogo-servicios-especialidades-maestro`, conversor) | servicio según catálogo maestro DPM | clave | — | grupo | Infosalud catálogos | eventual (may 2026) |
| Periodo | año / semana estadística (`catalogo-maestro-semanas-estadisticas`) | corte temporal oficial | fecha | — | grupo | Infosalud catálogos | semanal (cierres) |
| Casos | por identificar | número de casos del rubro | entero | egresos/consultas/cirugías/sesiones | suma | rubro del portal por identificar | por observar |
| Población | PAMF/PAU (por confirmar) | derechohabientes adscritos | entero | personas | suma | rubro Población por identificar | por observar |
| Indicador FN-19 | — | casos ÷ población × 1,000 | decimal | por 1,000 | derivado | CEPI | — |
| Demanda FN-20 | — | población zona × indicador ÷ 1,000 | decimal | casos esperados | derivado | CEPI | — |

## F. Resultado de conciliación

**No ejecutada.** La prueba mínima requiere casos por
unidad/servicio/periodo y un universo poblacional del mismo
corte; hoy no existe en el catálogo local ninguna fuente de
casos registrada ni URL conocida de los rubros (403 en
listados). Cualquier número que se produjera ahora sería
invención. La prueba quedará lista cuando: (1) existan las
URLs de listado histórico de los rubros elegidos o los
archivos guardados localmente; (2) se registren con
`fuente-alta` + `url_listado` (ADR-012); (3) el área
proporcione un total oficial de referencia para un OOAD y
año conocido. Con esos insumos, `fuente-exportar` (ADR-011)
puede producir CSV/SQLite agregados y auditar la suma del
OOAD contra el total oficial.

## G. Brechas y preguntas para CTIM

1. **URLs**: páginas de listado histórico por rubro
   (Estadísticas Nacionales, Censos, Consulta Externa,
   Hospital, Población) o, como plan B, archivos guardados
   localmente. El 403 bloquea el descubrimiento automático.
2. **Denominador oficial**: ¿FN-19/FN-20 usan PAMF, PAU o
   población usuaria? ¿Con qué corte (año estadístico vs
   año calendario)? ¿Quién es el responsable del dato?
3. **Zona de Influencia**: ¿existe tabla oficial de
   regionalización (unidades ↔ zona) con clave estable? El
   catálogo OOAD no la incluye.
4. **SIAIS**: ¿existe exportación institucional autorizada de
   productividad SIAIS (1N/2N/3N) por unidad, servicio y
   periodo, con estado definitivo/preliminar explícito?
   ¿Quién confirma su semántica?
5. **DataMart**: estado formal (vigente/baja) y sistema
   sucesor; qué tablas de productividad sobrevivieron y con
   qué claves.
6. **Duplicidad al sumar OOAD**: reglas oficiales para
   unidades compartidas o movimientos entre cortes.
7. **Tableros DPM** (Egresos, Día Típico, SIMOC, IDS, MMIM):
   ¿existe exportación mecanizable detrás de cada vista y
   diccionario de indicadores?
8. **Defunciones 2004–2025**: confirmar si algún rubro CEPI
   la requiere como numerador (no parece, pero conviene
   cerrarlo).

## H. Recomendación

- **Fuente apta**: ninguna hoy. Ningún candidato está
  capturado, observado en estructura ni conciliado.
- **Apta con condiciones** (hipótesis de trabajo):
  - Rubros del portal "Consulta Externa", "Hospital" y
    "Estadísticas Nacionales" como portadores de casos
    agregados, una vez registrados y observados (son
    archivos oficiales DIS, periódicos, agregados por
    unidad/servicio).
  - Rubro "Población" (PAMF/PAU) como denominador, con
    confirmación expresa del área de que es el universo de
    FN-19/FN-20 y del corte coincidente.
  - Catálogos ya capturados (OOAD, servicios maestro,
    conversor, semanas) como capas de claves y periodos.
- **No apta como fuente** (sólo apoyo): tableros Tableau
  (SIMOC, Egresos) — no descargables como archivo; el
  tablero no basta como fuente. IFU/CUUMSP/regionalización
  sólo para cruces, salvo campo de productividad documentado.
- **Evidencia insuficiente** para: SIAIS productividad
  nacional 1N/2N/3N, SUI, SIMF interno, DataMart y sucesor.
  No se afirma que SIAIS sustituya a DataMart: esa hipótesis
  exige casos por unidad/servicio/periodo, conciliación con
  totales oficiales y confirmación semántica del área
  propietaria — nada de los tres está demostrado.

Siguiente paso concreto (sin requerir CTIM): con las URLs de
listado (o archivos locales), registrar los rubros y correr
la prueba mínima en un OOAD conocido; el pipeline
`vigencia-verificar` → `fuente-campos` → `fuente-exportar`
ya soporta el ciclo completo en modo sólo lectura.

## Addendum (2026-09-02): el portal expone los insumos por puerto 80

El hallazgo de navegación (ver `docs/mapa-portal.md`) cambia el
estado de la investigación: la raíz por puerto 80 responde 200 y
los modales del menú cargan `/fragmentos/seccion/1..11` con los
enlaces directos a los archivos. Los tres huecos del bloque
"SABEMOS" original quedan resueltos a nivel *localización*:

- **PAMF localizado y registrado**: `poblacion-pamf-siais-2025`
  (`ARCHIVOS/poblacion/SIAIS/SIAIS_PAMF_Junio_2025_ver1_2026-02-24.xlsx`,
  200 OK, 13.8 MB), serie 2007–2025 con corte junio. Es el
  denominador candidato natural de FN-19/FN-20.
- **Total Consultorios MedFam PAMF localizado y registrado**:
  `poblacion-consultorios-medfam-pamf-2025`, serie 2018–2025.
- **Numeradores (casos) localizados**: productividad semanal
  estadística xlsx (`seguimiento-productividad-semanal-2025`,
  semana 52 cierre 2025-12-21), series homologadas de Consulta
  Externa 2012–2024 (Especialidades, Urgencias, Med Fam, Dental),
  Egresos 2012–2024 por OOAD-UMAE y por unidad médica,
  Intervenciones Qx, Partos/Cesáreas y UCI (fragmentos 2, 3 y 11).
- **IFU localizado**: páginas anuales `paginas/ifu_YYYY.html`
  2012–2026 (fragmento 6) y tablero `CifrasGenerales/IFU`
  (fragmento 11). Aún no registrado (es página índice, no archivo).
- **Pista de DataMart**: el tablero de Subrogados al cierre mensual
  se llama `SERVICIOSMEDICOSSUBROGADOSCIERREMENSUAL/
  SUBROGADOS_DataMart` — evidencia directa de que la capa DataMart
  alimenta al menos un tablero vigente. Pregunta 5 de §G sigue
  abierta pero ya no es "estado desconocido".

Efecto sobre la matriz (§D): las filas "Población (denominador)",
"Claves de unidad" y parcialmente "Hospitalización", "Consultas de
especialidades" y "Urgencias" pasan de *evidencia insuficiente* a
**localizadas con URL directa y en proceso de captura/estructura**.
La prueba mínima de §F ya es ejecutable: los archivos están
alcanzables y el área sólo debe dar el OOAD y el total oficial de
referencia. El corte junio del PAMF vs año estadístico de los casos
sigue siendo la condición crítica de coincidencia de universos.