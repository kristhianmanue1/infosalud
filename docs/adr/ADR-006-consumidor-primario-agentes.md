# ADR-006: Consumidor primario = agentes de IA; salida JSON de la CLI

Estado: aceptado (implementación no iniciada)
Fecha: 2026-09-01
Sustituye parcialmente a: la orientación de D3 en
`docs/f0-analisis.md` §6.4 (humano-first en v1).

Contexto: el humano redefinió el enfoque del proyecto (conversación
2026-09-01): el sistema está enfocado a **agentes de IA que consuman
los recursos de Infosalud**; los usuarios humanos pasan a segunda
línea, no primera. ADR-003 fijó la CLI como interfaz v1 pensada para
el humano; este ADR reordena el consumidor sin descartar la CLI.

Decisión: el consumidor primario de la v1 es un agente de IA. La CLI
de `CONTRATO: cli-infosalud v1` pasa a v1.1 añadiendo la opción
`--json` en todos los comandos: salida estructurada, determinística
y parseable (un objeto JSON por ejecución en stdout, diagnóstico en
stderr). La salida en texto plano se conserva para el humano.

Alternativas descartadas:
  - API HTTP local para agentes: reintroduce un proceso servidor y
    superficie de red que ADR-004/SPEC-3 prohíben en la v1; un
    agente invoca procesos con la misma naturalidad.
  - Reescribir la interfaz como librería sin CLI: perdería el
    contrato observable y los casos de prueba DADO/CUANDO/ENTONCES
    ya definidos.

Consecuencias: gana un consumidor primario no humano con contrato
cerrado y salidas determinísticas (JSON válido, códigos de salida
estables), y conserva al humano con la misma interfaz. Pierde la
pureza "humano-first" de la v1 original. Obliga: toda salida
`--json` debe ser JSON parseable con schema estable; un cambio de
campos exige v1.2/v2 según compatibilidad. Los agentes quedan
sujetos a las mismas prohibiciones (cero red, cero datos
personales); nada de este contrato autoriza a un agente a operar
fuera del entorno local.
