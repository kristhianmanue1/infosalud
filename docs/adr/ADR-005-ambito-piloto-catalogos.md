# ADR-005: Ámbito de la v1 = sección "Catálogos para los SIS"

Estado: aceptado (implementación no iniciada)
Fecha: 2026-09-01

Contexto: D4 (cerrar el ciclo completo sobre una sola sección antes
de escalar) exige elegir la sección piloto (PREGUNTA-4). El portal
ofrece al menos doce secciones (EV-14).

Decisión: la v1 cubre exclusivamente la sección "Catálogos para los
SIS" (unidades médicas, CIE-10, CIE-9, especialidades, semanas y
afines).

Alternativas descartadas:
  - Empezar por "Estadísticas Nacionales" o "Seguimiento
    Diario/Semanal": mayor volumen y periodicidad más agresiva,
    justo donde la falta de autorización (PREGUNTA-1) duele más.
  - Varias secciones a la vez: repite el patrón de error que F0
    registró como riesgo (hacer mucho antes de cerrar el ciclo);
    contraviene D4.

Consecuencias: gana un ciclo F0→F3 completo y verificable sobre un
dominio estable y de alta utilidad (los catálogos alimentan a MOCE,
IFU y los demás SIS). Pierde cobertura inmediata del resto del
portal; cada sección nueva se incorporará con una revisión de esta
decisión (nuevo ADR o actualización del enum `seccion` del contrato,
lo que exige versión nueva del mismo si rompe compatibilidad).
