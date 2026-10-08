# ADR-016: dimensión canónica `unidades` y cobertura de llaves

Fecha: 2026-10-08 · Estado: aceptado · Supervisa: ADR-014 (fase 4,
dimensiones) y ADR-006 (consumidor primario agentes)

## Contexto

Las fuentes integradas comparten la llave maestra Clave
Presupuestal, pero cada una vive en su isla y los universos NO son
idénticos (medido 2026-10-08: CUUMSP septiembre 1,563 unidades; IFU
agosto 1,584, con 25 unidades de apoyo UA 2110 fuera del CUUMSP;
Población agosto 1,288, con 17 fuera; intersección triple 1,271).
El análisis completo está en
`docs/analisis-relaciones-fuentes-2026-10.md`; la revisión previa,
en `docs/ronda-adversarial-2026-10-08.md`.

## Decisión

Servir un **maestro canónico de unidades** como dimensión
`unidades` del mecanismo `/dimensiones` existente (ADR-014 fase 4):
clave Clave Presupuestal → CLUES, delegación, entidad, municipio,
CP, georreferencia y nombres, proyectado del CUUMSP verificado más
fresco. El cruce analítico permanece en el consumidor (ADR-006); la
plataforma garantiza la llave y publica la cobertura.

Políticas:

1. **Referencia concreta, no "el más reciente"**: la config declara
   el id del corte; un corte nuevo no actualiza la dimensión solo.
   El refresco es deliberado, por `scripts/generar_dimension_unidades.py`.
2. **Unicidad fail-closed en generación**: el script rechaza declarar
   la dimensión si la clave no es única (H-1).
3. **Nombres verbatim del perfil** (H-2); atributos omitidos son
   error (H-6).
4. **Valores crudos** (H-3): la dimensión no coacciona tipos; las
   coordenadas viajan como texto y el consumidor las convierte.
5. **Cobertura registrada, no servida** (H-5): los conteos vs IFU y
   Población quedan en este ADR y en el análisis; endpoint propio
   pospuesto a demanda (F3).

## Cobertura registrada (2026-10-08, maestro = CUUMSP septiembre)

- IFU agosto: 1,559/1,584 dentro; 25 fuera (UA 2110).
- Población agosto: 1,271/1,288 dentro; 17 fuera.
- Intersección triple: 1,271.

## Alternativas descartadas

- **Join solo en el consumidor**: sin garantía de cobertura, coste
  repetido por pregunta (maestros de 0.5-1.5 MB por consulta).
- **Vistas enriquecidas /datos?enriquecer=**: acoplamiento entre
  fuentes, payload multiplicado, ETag complejo.
- **Proyecto relacional nuevo**: fuera de alcance v1 (stdlib, sin
  estado transaccional); revisar si aparece consulta de alta
  frecuencia.

## Consecuencias

- El agente descarga la dimensión una vez (~0.3 MB, ETag) y cruza
  localmente cualquier fuente por Clave Presupuestal.
- Con cada corte nuevo del CUUMSP se corre el generador (F2): la
  dimensión se re-declara y la cobertura se re-mide.
- Limitación aceptada: el runtime no detecta claves duplicadas si la
  config se edita a mano fuera del generador (H-1).
