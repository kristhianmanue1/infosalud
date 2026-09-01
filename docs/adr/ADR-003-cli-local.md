# ADR-003: Interfaz humana v1 = CLI local

Estado: aceptado (implementación no iniciada)
Fecha: 2026-09-01

Contexto: D3 (humano-first en v1) y REQ-4 exigen una vía para que el
humano consulte el catálogo. La elección de interfaz es estructural:
define la frontera del contrato CLI.

Decisión: la interfaz de la v1 es una CLI local
(`CONTRATO: cli-infosalud v1`), sin servidor.

Alternativas descartadas:
  - Aplicación web local: más cómoda para explorar, pero introduce
    un proceso servidor y una superficie de red que la v1 prohíbe
    (SPEC-3: cero red); sin requisito que la pida todavía.
  - Notebook/consola interactiva: sin contrato estable; la frontera
    CLI da casos testables directos para F3 (la guía exige que cada
    caso DADO/CUANDO/ENTONCES sea traducible a test).

Consecuencias: gana trazabilidad (cada operación es un comando con
código de salida) y cero superficie expuesta. Pierde ergonomía
visual; una interfaz web local para exploración humana puede
añadirse en v2 con un ADR nuevo, consumiendo el mismo contrato de
catálogo. Queda prohibido que la CLI abra puertos o sockets.
