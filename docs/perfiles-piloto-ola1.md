# Perfiles estructurales — ola 1 del piloto CEPI (informe)

Fecha: 2026-09-04. Alcance: los 6 archivos registrados con el
hallazgo del puerto 80 (catálogo 23→29, 2026-09-02), que son la
base del piloto CEPI (P11, ADR-014).

## Resultado: 3 perfiles v1 en producción

| Fuente | Hojas perfiladas | Estado en `/datos` |
|---|---|---|
| `poblacion-pamf-siais-2025` | 4 (Consultorios, UM_Totales, OOAD, No_Consideradas) | aplicado, `fuera_de_rango: 0` |
| `poblacion-consultorios-medfam-pamf-2025` | 4 (Tot_Cons_MedFam, Tot_Cons_MF_OOAD, PAMF_Consultorios, NO CONTEMPLADAS) | ídem |
| `poblacion-usuaria-23n-simoc-unidad-2025` | 2 (Esp, Urg; fila 12 = total nacional en `filas_total`) | ídem; totales aparte |

Generación semi-automática (P11): `scripts/generar_perfiles_piloto.py`
extrae las columnas de la fila de encabezados declarada, valida con
el contrato `perfil-de-fuente v1` (SPEC-11) y escribe
`data/perfiles/<id>.json` (versionado en git, P12). Verificación en
vivo contra el contenedor `1nf0541ud`: `perfil_aplicado: true` y
`requiere_revision: false` en las 10 hojas.

## No perfilados en esta ola (con causa)

| Fuente | Causa | Camino |
|---|---|---|
| `poblacion-usuaria-1n-unidad-2004-2025` | xls binario, sin lector (P11: bloqueados fuera hasta el ADR de lectores) | conversor LibreOffice (patrón ya usado para IFU dic-2025) |
| `estadisticas-nacionales-cifras-2025` | encabezados compuestos de dos filas (grupo fila 3 + subgrupo fila 4) que `perfil-de-fuente v1` no expresa; 10 hojas con layouts propios | extender el perfil (p. ej. `fila_encabezados: [3,4]`) con enmienda compatible, o perfil dedicado por hoja |
| `seguimiento-productividad-semanal-2025` | multi-bloque (varias tablas por hoja, notas intercaladas) | ídem; requiere diseño antes de declarar rangos |

## Hallazgos del perfilado

- Los archivos SIAIS traen portada/títulos (filas 1-7) y
  encabezados en fila 7-11 según el archivo — exactamente lo que
  el perfil formaliza; sin él, la lectura cruda mezcla portada
  con datos.
- Subtotales embebidos dentro del rango de datos (PAMF:
  `Consultorio=9999/Turno=99` por unidad; `99999` en UM_Totales):
  declarados en `notas` del perfil; la conciliación automática
  (parser numérico + tolerancia, corrección adversarial #5) es
  fase 3 y los detectará como filas de total.
- `fuera_de_rango` sólo cuenta contenido DESPUÉS del rango
  declarado: los títulos/encabezados previos son estructura
  legítima, no pérdida silenciosa.