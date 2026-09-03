# ADR-014: Perfiles estructurales, datos normalizados (nivel 2) y
# auditoría por agente de IA

Estado: aceptado (fase 1 implementada en esta misma rama: contrato
`perfil-de-fuente v1` + validador `infosalud/perfiles.py` + SPEC-11
+ tests; fases 2–4 —endpoint `/datos`, dimensiones, auditoría—
pendientes, cada una con SPEC y tests propios)
Fecha: 2026-09-03

Contexto: el servicio (ADR-013) es un servidor de archivos con
metadatos de procedencia de calidad excepcional (huella sha256,
vigencia, integridad en vivo), pero los consumidores siguen teniendo
que descargar contenedores opacos (xlsx/xls/zip) y parsearlos ellos.
El análisis de arquitectura (§3) define tres niveles del mismo dato:
(1) archivo original —ya existe—, (2) datos normalizados y
(3) vistas agregadas. El análisis de datos y auditoría (§A–E)
especifica perfiles, relaciones por dimensiones canónicas y
auditoría en dos niveles. Ambos análisis fueron atacados en la
ronda adversarial de diseño (2026-09-03), que produjo correcciones
obligatorias antes de aceptar este ADR.

Decisión:
1. **Perfil estructural versionado** (contrato nuevo
   `perfil-de-fuente v1`, docs/f1-contratos.md; artefacto en
   `data/perfiles/<id>.json`, versionado en git —P12—): por hoja,
   declara `tipo` de hoja, `fila_encabezados`, `columnas`,
   `filas_datos {desde, hasta}`, `clave_primaria`, `claves_foraneas`
   (hacia `/dimensiones/*`), columnas numéricas, fila(s) de
   total/subtotal y tolerancia de reconciliación. La normalización
   NO depende de heurísticas re-ejecutadas: lo que está fuera del
   rango declarado no entra al dato (los totales se declaran, no se
   "detectan" al vuelo). Las filas de total se sirven aparte
   (`segmentos: {datos, totales}`): separación, no eliminación.
2. **Datos normalizados (nivel 2)**: `GET /fuentes/{id}/datos`
   (+ `?hoja=`) y tool MCP `datos_fuente`, leídos del archivo
   verificado con el lector existente (`estructura.leer_filas`,
   ADR-010/011). Regla de oro: todo nivel derivado declara su
   `sha256` de origen — la procedencia nunca se pierde. Tope de
   filas por respuesta (reusar MAX_FILAS de exportar; P4).
   - **ETag compuesto** (corrección adversarial #1): NO la huella
     sola — `ETag = sha256(huella_archivo + sha_perfil +
     forma_de_respuesta)`, con `304` ante `If-None-Match`. La
     huella sola sólo sirve para `/archivo`.
   - **Cache-Control**: `public` sólo mientras el API sea abierto;
     con token activo → `private, no-store` (corrección #2).
3. **Pérdida silenciosa contenida** (corrección #4): tras
   normalizar se cuentan filas con contenido fuera del rango
   declarado y se expone `fuera_de_rango: n`; `n > 0` → estado
   `requiere_revision` (disparador del nivel 1 de auditoría).
4. **Dimensiones canónicas como endpoints de primera clase**:
   `/dimensiones/unidad`, `/dimensiones/servicio`, etc., derivadas
   de los catálogos ya verificados (con huella). Cada dataset
   declara sus claves; métrica obligatoria de **cobertura de clave**
   (% de filas que resuelven contra la dimensión, reportada visible,
   no error). Tabla de **alias** por sistema de origen y **ciclo
   propio de vigencia** con fecha de corte visible (el catálogo OOAD
   vence; corrección #6). Una relación entre dos fuentes sólo
   existe si ambas declaran la misma dimensión. Los joins con
5. **Auditoría en dos niveles con disparadores distintos** (§D):
   - Nivel 1 — diff estructural automático: lo dispara
     `vigencia-verificar` al detectar huella nueva; compara contra
     el perfil vigente (hojas/columnas/rangos). Veredicto:
     `conforme` o `requiere_revision`.
   - Nivel 2 — auditoría lógica (agente, programada o bajo demanda,
     y siempre tras un nivel 1 adverso): reconciliación de totales,
     cobertura de claves, comparación contra total oficial.
   - **Veredicto advisory** (corrección #3): el agente sólo puede
     marcar `requiere_revision`; `rechazada` exige confirmación del
     área/humano y segunda opinión (P10) antes de elevarse. El
     informe es artefacto versionado
     (`data/auditorias/<id>/<fecha>.json`) que registra modelo,
     versión y fecha, y cuyo propio sha256 queda en el checkpoint
     de AN-KLA. Nunca sobrescribe el dato: sólo lo califica.
   - **Visibilidad pasiva** (P9): los estados se exponen donde el
     área ya mira — `/healthz` con conteo por `estado_semantico` y
     `/cobertura` con columna de estado (sin correo, stdlib).
6. **Reconciliación numérica robusta** (corrección #5): parser
   numérico con normalización (comas de millar, símbolos), columnas
   numéricas y tolerancia declaradas en el perfil, soporte de
   múltiples filas de total/subtotal; reporta
   `reconciliado: true/false` con lo hallado.
7. **Perfiles a escala por olas** (P11): (a) los 6 del piloto CEPI,
   (b) datos de consumo frecuente (series 2012–2024), (c) resto;
   los formatos bloqueados (xlsb, html) quedan fuera hasta el ADR
   de lectores. El borrador asistido (ADR-010) genera el perfil y
   el auditor de nivel 1 lo valida — flujo semi-automático.
8. Cambios de forma de respuesta ⇒ versión del contrato
   (`servicio-infosalud`): lo additive mantiene v1; lo incompatible
   exige v2. Toda ampliación con tests DADO/CUANDO/ENTONCES.

Alternativas descartadas:
   - Parsear al vuelo con heurísticas re-ejecutadas: resultado no
     determinista entre corridas; el perfil lo persiste versionado.
   - ETag = huella del archivo: cachés sirven datos viejos si el
     perfil cambia con el mismo archivo (corrección adversarial #1).
   - Veredicto automático `rechazada` por el agente: un modelo no
     determinista tomando decisión de gobernanza sin humano.
   - Base de datos (Postgres) ahora: stdlib basta para el nivel 2;
     el paquete Postgres es un consumidor posterior (análisis
     postgresql-futuro) y no condiciona esta decisión.
   - Servir datos sin procedencia: rompe la regla de oro del
     sistema (huella = verdad en todo nivel).

Consecuencias: gana un nivel de consulta (el agente consulta, no
parsea), caching determinista por contenido, calidad medible
(reconciliación, cobertura) y gobernanza de veredictos sin ceder
autoridad al modelo. Pierde simplicidad: un contrato y artefacto
nuevo por fuente (el perfil es la parte cara — por eso las olas),
dos endpoints y una tool MCP más que mantener, y el riesgo residual
de perfiles desactualizados (contenido por `fuera_de_rango` +
`requiere_revision`, no silencioso). Requiere implementación por
fases (endpoint `/datos` → dimensiones → auditoría nivel 1 →
nivel 2), cada una con SPEC y tests.
   validez temporal (SCD2 simplificado, P5) quedan como requisito
   del consumidor del paquete, no del servicio v1.