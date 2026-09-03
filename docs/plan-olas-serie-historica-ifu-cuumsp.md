# Plan por olas: serie histórica IFU / CUUMSP (2026-09-03)

Objetivo: completar la serie histórica preservada de IFU
(`paginas/ifu_YYYY.html`, 2012–2026) y CUUMSP
(`paginas/cuumspYYYY.html`, 2021–2026) por olas acotadas, con el
mismo patrón de la entrega CEPI (parent_source_id, aliases,
corte_declarado, huella sha256). Estado de partida: 2026 completo
(mensuales) + dic-2025 IFU + dic-2025/agosto-2026 CUUMSP = 70
fuentes en catálogo.

Reglas (heredadas, no nuevas):
- Descarga GET de sólo lectura al portal (patrón ADR-008/012);
  nada se infiere sin archivo descargado y verificado.
- Sin interpretación semántica de campos (limitación de la entrega
  CEPI §9); estructura sólo para xlsx/xls legibles.
- Cada archivo nuevo = fuente hija con `parent_source_id` hacia su
  página índice del año; `corte_declarado` = mes/año del nombre;
  alias "IFU"/"CUUMSP" + mes + año.
- xlsb: se registran con formato `otro` y quedan sin estructura
  hasta el conversor (patrón LibreOffice headless ya usado).
- Toda ola termina en commit en rama propia + informe en
  `docs/`; el catálogo queda íntegro (fail-closed ante fallos).

| Ola | Alcance | Volumen | Formatos |
|---|---|---|---|
| 1 | CUUMSP 2025 (mensuales faltantes) | ~11 | xlsx |
| 2 | CUUMSP 2021–2024 (nuevo→viejo) | ~48 | xlsx (2021–23 por confirmar) |
| 3 | IFU 2025 (mensuales faltantes) | ~11 | xlsb (estructura: conversor) |
| 4 | IFU 2012–2024 (nuevo→viejo) | ~150 | xlsb/xlsx mixto |
| — | Tableros Tableau | 0 | no descargables (fuera de alcance) |

Orden de las olas: primero CUUMSP (xlsx legible hoy, mayor valor
por el diccionario embebido y la hoja Histórico), después IFU
(bloqueada parcialmente por el lector xlsb en las olas 3–4: los
archivos se preservan, la estructura llega con el conversor).

Pendiente de autorización antes de ejecutar cualquier ola:
- Confirmación del humano sobre alcance y volumen (cada ola toca
  el portal decenas de veces; PREGUNTA-1 de consulta automatizada
  sigue abierta).
- Verificar que cada página índice anual responde 200 al cliente
  (el 403 generalizado sólo aplica a la raíz `:8080`; mapa-portal
  §Actualización 2026-09-02).

Ejecución por ola (checklist):
1. GET de la página índice del año → lista de enlaces directos.
2. Alta de cada archivo faltante (id por convención de la entrega
   CEPI; resolver antes la normalización de ids pendiente §7).
3. Descarga + huella + verificación (`vigencia-registrar`).
4. Estructura donde el formato lo permita; diccionario borrador
   para los xlsx (patrón ADR-009/010).
5. Informe de la ola + commit; sin push sin autorización.