# ADR-015: Lock de catálogo — exclusión mutua para escritores
# concurrentes

Estado: aceptado (SPEC-10 e implementación en esta misma rama)
Fecha: 2026-09-03

Contexto: `guardar_catalogo` escribe atómicamente (temporal +
`os.replace`, SPEC-3): un fallo a medias nunca corrompe el archivo.
Pero toda escritura es un **read-modify-write completo**: el proceso
carga el catálogo, muta y reescribe TODO. Sin exclusión mutua, el
último guardado pisa al anterior. El incidente del 2026-09-02
(ronda adversarial, docs/ronda-adversarial-2026-09-02.md) lo
demostró con pérdida real de altas: alta manual concurrente con un
lote `vigencia-verificar`. Hoy conviven dos escritores (CLI de altas
manuales y el sondeo launchd de vigencia); con el cargador Postgres
serían **tres** (P13), y el afinamiento ordena redactar este ADR
ANTES de ese cargador. `docs/operaciones.md` ya documenta la
mitigación operativa actual (nunca alta manual + lote en paralelo),
que es disciplina, no garantía.

Decisión:
1. **Lock advisory exclusivo por proceso** con `fcntl.flock`
   (stdlib, POSIX) sobre un archivo lateral
   `data/fuentes.json.lock`: se adquiere ANTES de leer el catálogo
   y se libera al terminar de guardar — todo el read-modify-write
   queda dentro de la sección crítica. Ofrecido como context
   manager en `infosalud/catalogo.py`; la CLI lo usa en todo camino
   que escribe (fuente-alta, vigencia-registrar, vigencia-verificar
   y su lote).
2. **Adquisición con espera acotada**: intento no bloqueante con
   reintentos breves hasta un tope total (~30 s). Vencido el tope:
   fallo con mensaje claro, código de salida 1 y **sin escribir**
   (fail-closed). Nunca bloquear indefinidamente un proceso
   atendido por launchd.
3. **El archivo de lock no se borra** tras usarlo: borrarlo introduce
   la carrera clásica de unlink/recreación. Un archivo vacío
   persistente es el precio mínimo.
4. **Los lectores no toman el lock**: el servicio (ADR-013) y la
   CLI de lectura siguen leyendo sin lock — la lectura es segura
   porque la escritura es atómica por `os.replace`; un lector ve el
   archivo viejo o el nuevo, nunca uno a medias.
5. Alcance: el lock protege `data/fuentes.json` (y por la misma
   sección crítica, cualquier archivo derivado que el escritor
   actualice junto). No sustituye la verificación de integridad ni
   el historial append-only; los complementa.
6. Implementación y SPEC: SPEC-10 (docs/f1-specs.md) con casos
   DADO/CUANDO/ENTONCES en `tests/` — dos procesos: el segundo
   espera y procede, o falla acotado si el lock no se libera;
   ningún guardado se pierde.

Alternativas descartadas:
   - Disciplina de escritor único (status quo): ya falló con
     pérdida real de altas; la disciplina no escala a tres
     escritores.
   - Comparar-y-intercambiar por campo `version` con reintentos y
     merge manual: semántica de fusión compleja para un catálogo
     de lista; el lock serializa sin política de merge.
   - Lock por directorio (`os.mkdir`): portable, pero deja basura
     tras un crash y exige staleness manual; `flock` se libera solo
     al morir el proceso.
   - Migrar ya a SQLite/Postgres: resuelve concurrencia de paso,
     pero es un cambio de storage mayor (análisis
     postgresql-futuro) que no debe ser el precio de un lock;
     ADR-001 sigue mandando stdlib.
   - Last-writer-wins documentado: es exactamente el comportamiento
     actual que perdió las altas.

Consecuencias: gana la garantía de que ninguna escritura completa
pisa a otra, con stdlib puro y sin cambiar el formato del catálogo
(contratos intactos); habilita con seguridad el cargador Postgres
como tercer escritor. Pierde: un archivo lateral más en `data/`,
una espera acotada en el peor caso (30 s) y acoplamiento a POSIX
(`fcntl` no existe en Windows — irrelevante: el despliegue es
macOS + Linux contenedor). Riesgo residual: un proceso que guarde
fuera del context manager evade el lock — se mitiga con tests que
fallan si algún camino de escritura de la CLI no usa el
context manager.