# ADR-010: Borrador asistido del diccionario (muestreo y hoja descriptiva)

Estado: aceptado (autorización humana 2026-09-01: "adelante con
pendientes 1 y 2"; la observación de que muchos archivos traen hoja
descriptiva —p. ej. "Metadatos y equivalencia" en el CIE-10— queda
incorporada como requisito de análisis)
Fecha: 2026-09-01

Contexto: ADR-009 dejó el significado de los campos como trabajo del
área. El humano pidió agilizarlo: el sistema puede hacer el trabajo
pesado de observación y el área sólo validar. Además, muchos
catálogos traen una hoja descriptiva (metadatos, equivalencias,
notas de uso) que hoy se ignora y que contiene conocimiento
institucional ya publicado por la fuente.

Decisión:
  1. `fuente-campos <id> --borrador`: analiza el archivo local ya
     verificado de la fuente (última verificación con huella) y
     enriquece el diccionario SOLO con evidencia observada:
     - `ejemplo` y `valores` (dominio muestreado, máx 5 valores) de
       cada campo sin esos datos; nunca sobrescribe lo declarado.
     - `metadatos`: contenido de las hojas descriptivas detectadas.
  2. Detección de hoja descriptiva (heurística declarada, dos
     reglas): (a) el nombre de la hoja sugiere descripción
     (metadatos, notas, equivalencias, instrucciones, glosario,
     definiciones...), o (b) su primera fila tiene ≥70% de celdas
     vacías (no es encabezado tabular). Las filas de una hoja
     descriptiva se leen como líneas etiqueta→contenido.
  3. Ninguna `descripcion` se genera ni se sobrescribe: el
     significado sigue siendo declaración humana (ADR-009). El
     borrador reduce el levantamiento a una revisión.
  4. `metadatos` se añade al CONTRATO diccionario-de-fuente v1 como
     campo opcional (compatible): lista de {hoja, metadatos: [{,
     contenido ≤500}]}, con topes (200 líneas por hoja).
  5. Si la fuente no tiene diccionario, --borrador lo crea como
     esqueleto desde la estructura observada de la última
     verificación y luego lo enriquece (un solo paso).

Alternativas descartadas:
  - Generar descripciones con el agente sin validación humana:
    contraviene ADR-009; una descripción inventada es peor que una
    ausente.
  - Analizar el archivo en cada verificación de vigencia: mezcla
    responsibilities y encarece el comando caliente; el borrador es
    una operación explícita y aparte.
  - Requerir que el humano ubique la hoja descriptiva a mano:
    fricción innecesaria; la heurística es simple y auditable.

Consecuencias: gana un levantamiento de diccionarios casi automático
(el área revisa en vez de capturar) y rescata el conocimiento ya
publicado en hojas descriptivas. Pierde simplicidad: heurística de
clasificación de hojas que puede fallar (un falso descriptivo no
contamina campos: sólo metadatos); dependencia de que exista archivo
local verificado.
