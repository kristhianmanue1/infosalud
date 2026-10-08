# Análisis: relaciones entre fuentes y cómo servirlas a agentes

Fecha: 2026-10-08 · Alcance: arquitectura de consumo · Estado:
análisis para decisión (si se aprueba, crea ADR-016)

## 1. Pregunta

Los catálogos y series ya integrados comparten llaves (Clave
Presupuestal, CLUES, OOAD). Los usuarios son agentes de IA (ADR-006).
¿La plataforma debe servir las relaciones entre fuentes, o el cruce
queda en el consumidor? ¿Corresponde un proyecto nuevo?

## 2. Inventario de llaves de cruce (medido en los archivos)

- **Clave Presupuestal (12 pos)** — CUUMSP (todos los cortes), IFU
  nacional, Población Adscrita, IFU BAJAS/Solicitudes y seguimiento
  productividad. Llave maestra de unidad.
- **CLUES** — sólo el CUUMSP la trae.
- **Clave OOAD (2 pos: 01-34 + 4A-4Y)** — IFU, Población Adscrita y
  catálogo OOAD/subdelegaciones. La dimensión canónica `ooad` ya
  existe.
- **Entidad / Municipio / CP (INEGI)** — CUUMSP, IFU (Entidad) y
  catálogo CPxUMF. Geografía.
- **CVE servicio / especialidad** — catálogo servicios-especialidades,
  conversor SIMO/MOCE y SIAIS. Dimensión `servicio` ya declarada.
- **CIE-10** — catálogos CIE-10 (CEMECE, SIMF maestro) y SIAIS
  CIE-10 EPI/IM. Dimensión diagnóstica.
- **Semana estadística** — catálogo maestro semanas y seguimiento
  productividad. Dimensión temporal.

## 3. Evidencia de cobertura (cortes vigentes, medido 2026-10-08)

| Universo | Unidades |
|---|---|
| CUUMSP septiembre 2026 | 1,563 |
| IFU agosto 2026 | 1,584 |
| Población Adscrita agosto 2026 | 1,288 |

- IFU ⊆ CUUMSP: 1,559/1,584 — **25 unidades fuera**: todas `UA 2110`
  (unidades de apoyo UMAA) que el CUUMSP no lista.
- Población ⊆ CUUMSP: 1,271/1,288 — **17 fuera**.
- Intersección triple: 1,271 unidades.

Conclusión: **los universos no son idénticos**. Un join ingenuo descarta
filas sin avisar. La plataforma no debe ocultar esa diferencia: debe
publicarla (cobertura por fuente como dato de primera clase).

## 4. Opciones

### A. El consumidor cruza (status quo)
El agente descarga /datos de cada fuente y hace el join local.
- Pros: cero complejidad nueva; máximo flexibility analítica.
- Contras: un cruce típico exige traer `Unidad` del IFU (1,584 filas ×
  200 columnas) y/o CUUMSP (1,563 × 40) por cada pregunta; sin garantía
  ni visibilidad de cobertura; cada agente reinventa la misma unión;
  sin ETag del conjunto.

### B. Dimensiones canónicas servidas (evolución del mecanismo actual)
El servicio ya expone `/dimensiones/{nombre}` (ooad, servicio,
subdelegacion declaradas en data/dimensiones.json). Extenderlo:
- **Dimensión `unidades`**: maestro por Clave Presupuestal con CLUES,
  OOAD, entidad, municipio, CP, lat/lon y nombre oficial, construido
  desde el CUUMSP más fresco y contrastado contra el catálogo OOAD
  oficial.
- **Reporte de cobertura**: para cada fuente tabular, unidades
  presentes vs maestro (los 25 y 17 de arriba, publicados como dato).
- Pros: determinista, versionado, ETag; el agente descarga una
  dimensión (~1,600 filas × ~12 columnas) y cruza localmente contra
  cualquier fuente; un solo lugar para auditar la llave maestra.
- Contras: exige refresco disciplinado cuando llega un corte nuevo
  (script por lote, igual que los perfiles).

### C. Vistas enriquecidas del servicio (/datos?enriquecer=unidades)
El servicio inyecta atributos de unidad en cada fila de /datos.
- Pros: conveniencia máxima.
- Contras: acopla fuentes entre sí (un corte del IFU quedaría atado al
  CUUMSP vigente), multiplica el payload (contra el objetivo de
  presupuestos acotados de ADR-006), complica el ETag compuesto y la
  auditoría. Descartada por costo/beneficio.

### D. Proyecto nuevo (motor relacional / grafo)
Fuera de alcance v1: dependencias fuera de stdlib o un estado
relacional propio duplicarían lo que el join local del agente ya hace
bien. No justificado con la evidencia actual; revisar si aparece
consulta transaccional multi-fuente de alta frecuencia.

## 5. Recomendación

**Opción B**, como evolución del mecanismo de dimensiones existente, y
mantener **A** como modelo de consumo para analítica ad hoc:

1. **F1**: dimensión canónica `unidades` desde CUUMSP septiembre 2026
   (1,563 filas) con reporte de cobertura contra IFU agosto (25
   fuera: UA 2110) y Población agosto (17 fuera). Contracto
   `dimension-v1` ya servido por /dimensiones — no requiere código
   nuevo, sólo la entrada en data/dimensiones.json y su prueba.
2. **F2**: refresco por lote con cada corte nuevo del CUUMSP
   (extender scripts/generar_perfiles_cuumsp_lote.py o script
   hermano) + prueba de cobertura en la suite.
3. **F3 (opcional, bajo demanda)**: vista enriquecida si algún
   consumidor la pide con presupuesto de payload explícito.

La decisión formal, con sus alternativas, corresponde a un **ADR-016**
(cuando se apruebe esta recomendación).

## 6. Ejemplo de coste para un agente (opción B)

Pregunta: "camas censables por entidad federativa contra población
adscrita". Hoy: traer IFU `Unidad` (≈1.5 MB JSON) + Población (≈0.5 MB)
y cruzar. Con dimensión `unidades`: traer la dimensión (~0.3 MB, ETag
estable) una vez; ambos /datos ya traen la Clave Presupuestal en cada
fila. El join deja de requerir descargar el maestro completo del
CUUMSP.
