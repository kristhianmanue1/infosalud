# Ronda adversarial 2026-10-08

Objeto: diseño de la dimensión canónica `unidades` (ADR-016, F1)
antes de implementar. Método: revisión del mecanismo
`infosalud/dimensiones.py` y del dato real (CUUMSP septiembre 2026,
IFU agosto, Población agosto).

## Hallazgos

- **H-1 — colapso silencioso de claves duplicadas**: `construir`
  arma un dict clave→atributos; si dos filas compartieran Clave
  Presupuestal, la segunda pisa a la primera sin avisar. Verificado:
  1,563 filas = 1,563 claves únicas en este corte, pero el runtime no
  lo detecta. *Tratamiento*: el generador verifica unicidad
  fail-closed antes de declarar la dimensión; limitación documentada
  en el ADR (si la config se edita a mano sin el script, sin red).
- **H-2 — nombres de columna con espacios irregulares**: el CUUMSP
  trae 'CLUES  Salud' (doble espacio), 'Nivel de Atención ' y
  'Fecha de Construcción ' (espacio final). El esquema exige
  coincidencia exacta con el perfil. *Tratamiento*: el generador
  resuelve los nombres verbatim desde el perfil (comparación
  normalizada, escritura literal) y verifica presencia antes de
  escribir la config.
- **H-3 — tipos crudos**: LATITUD/LONGITUD y fechas viajan como
  texto (celdas del xlsx convertidas a texto); `dimension-v1` no
  coacciona tipos. *Tratamiento*: servir crudo y documentarlo en el
  ADR; no inventar coerción fuera del contrato.
- **H-4 — frescura/deriva**: la dimensión referencia un id concreto
  (no "el más reciente"): un corte nuevo del CUUMSP NO la actualiza
  solo. *Tratamiento*: asumido como política — determinismo primero;
  el refresco es un acto deliberado por script (F2), nunca automático.
- **H-5 — cobertura no expresable en el esquema**: el reporte de
  cobertura (25 unidades del IFU y 17 de Población fuera del maestro)
  cruza varias fuentes; `dimension-v1` sólo proyecta una.
  *Tratamiento*: el generador la calcula y la registra en el ADR y en
  el análisis; endpoint dedicado pospuesto (F3, bajo demanda).
- **H-6 — atributos omitidos**: `construir` tolera atributos ausentes
  devolviendo 'atributos_omitidos'. *Tratamiento*: el generador trata
  cualquier omisión como error; el test la rechaza.
- **H-7 — integridad**: `construir` valida el sha256 local contra el
  registrado (409 si difiere). La dimensión hereda el fail-closed.
  *Verificación positiva en los tests.*
- **M-1 — 'Inicio de Productividad' serial de Excel**: valor críptico
  sin coerción. *Tratamiento*: excluido de los atributos v1; queda
  documentado en el diccionario de la fuente.
- **M-2 — filas de subtotal**: verificadas ausentes en 'Unidad
  Médica' (1,563 datos = 1,563 claves, sin TOTAL); el generador lo
  re-verifica en cada corrida.
- **L-1 — nombre**: la dimensión se llama `unidades` (plural, por
  contraste con `ooad`).

## Resultado

8 hallazgos tratados antes de implementar: 2 correcciones al plan
(H-1 unicidad en el generador, H-2 nombres verbatim), 2 decisiones de
alcance (H-3 crudo, M-1 exclusión), 2 políticas documentadas (H-4,
H-5) y 2 verificaciones añadidas a los tests (H-6, H-7).
