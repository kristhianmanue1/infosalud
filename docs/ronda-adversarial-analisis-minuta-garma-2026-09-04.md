# Ronda adversarial sobre el análisis de la minuta Garma — 2026-09-04

Objetivo: atacar el análisis crítico propio de la minuta
`codex/minuta-garma-origen-datos-20260904` antes de darlo por válido.
Método: refutación desde cero de cada crítica, verificando qué
evidencia real la respaldaba. La minuta describe un proyecto (frontend
React, backend con gate de cobertura, migraciones) no localizable en
este clon; la ronda aplica igualmente al método del análisis.

## Veredicto general

El análisis era direccionalmente correcto pero sobregarantizado:
usó evidencia fuera de alcance, postuló un riesgo sin soporte y
exigió cosas que la propia minuta ya declara cumplir. De 6
recomendaciones, 4 sobreviven (íntegras o debilitadas), 1 se retracta
y 1 se retracta parcialmente.

## Hallazgos sobre el análisis propio

- **H-1 (alta) — Evidencia fuera de alcance.** La tabla de
  verificación comparó "135 vigentes y 1 inaccesible" (catálogo
  completo) contra el checkpoint "17/17 vigente", que refiere sólo a
  la serie CUUMSP 2021–2026, no al catálogo total. Comparación
  inválida: el checkpoint no contradice el dato de la minuta; es
  simplemente no verificable desde este clon. Retractada.
- **H-2 (alta) — Riesgo inventado.** Se postuló "mezcla de periodos"
  en FN-19/FN-20 (PAMF junio 2025 + casos diciembre 2025) sin
  visibilidad del código: usar el último corte disponible de cada
  dominio puede ser diseño intencional. Retractado el riesgo;
  sobrevive sólo la recomendación defensiva de etiquetar periodo.
- **M-1 (media) — Búsqueda más angosta que la conclusión.** "No
  existe en esta máquina" derivó de sondas acotadas (sin `find -L`,
  profundidad limitada, un solo remote). Ante búsqueda incompleta el
  resultado honesto es `no_evaluado`, no `falso`. Aplica el
  principio fail-closed del proyecto a la inferencia propia.
- **M-2 (media) — Atribución injusta del gate.** La cobertura 41%
  es propiedad del código heredado completo, no del cambio actual;
  la minuta reportó el gate fallido honestamente. Sobrevive la
  propuesta de diff coverage con ADR; no la crítica de tono.
- **M-3 (media) — Recomendó lo ya existente.** La minuta ya declara
  que FN-05/FN-06 "se muestran como aplicación provisional". El
  valor agregado real se reduce a: etiqueta de periodo por fórmula y
  registro fechado de provisionales con bloqueo de extensión.
- **M-4 (media) — Acción prematura.** Presionar por commit inmediato
  puede consagrar una agregación (80364+80407) aún sin línea de SPEC
  citada. Prioridad correcta: preservar el trabajo (stash/patch
  referenciado); commit es segunda opción. Espejo de la regla local
  "el lote nunca pisa perfiles existentes".
- **L-1 (baja) — Exceso retórico.** "Afirmación de fe" era
  improcedente: la minuta da anclajes verificables (rama, HEAD,
  archivos, conteos). El fallo es de conciliación de entornos.
- **L-2 (baja) — Bloqueo posiblemente redundante.** El IFU
  convertido ya está acotado como vista de sólo lectura precargada;
  el candado pedido quizá ya existe por diseño. Queda como
  verificación a confirmar en código, no como bloqueo nuevo.
- **L-3 (baja) — Nombre de migración.** `t6u7v8w9x0y` puede ser
  identificador generado por herramienta; sobrevive sólo la mitad
  débil: documentar qué hace y a qué SPEC responde.

## Confirmado como correcto (sobrevive el ataque)

1. Conciliar proveniencia antes de actuar: ubicar el clon o rehacer
   el reporte contra el estado real.
2. Diff coverage como política formal (con ADR) en vez de exigir el
   90% global heredado.
3. Registro fechado de fórmulas provisionales con bloqueo de
   extensión a otros servicios hasta cierre CTIM.
4. Etiquetado de periodo en indicadores provisionales.
5. Documentar la migración (qué hace, a qué SPEC responde).
6. Preservar el trabajo no commiteado de forma verificable.

## Secuencia propositiva refinada

Conciliar proveniencia -> preservar (no necesariamente commitear) el
árbol -> política de cobertura con ADR -> registro CTIM de
provisionales -> verificar read-only y perfil semántico del IFU ->
documentar la migración.
