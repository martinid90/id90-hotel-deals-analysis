# Auditoría de código TP3 (completa y crítica)

Fecha: 2026-10-21

## Resumen ejecutivo

- Ambos grupos tienen API funcional, pipeline trazable y reglas explícitas.
- El principal problema detectado no es de infraestructura: es **metodológico/semántico** (unidad de precio y calibración de umbral).
- Hallazgos de mayor impacto:
  1. Ambigüedad de unidad de entrada en Grupo 02 (`price_total`) vs uso real en entrenamiento.
  2. Sensibilidad alta del recall en Grupo 02 bajo validación out-of-sample.
  3. Comportamiento deliberadamente conservador en Grupo 01 por regla `sospechoso`.

---

## Hallazgos por grupo

## Grupo 01

### H1 (Mayor) — Política conservadora explícita en precios extremadamente bajos
- Evidencia: regla de `sospechoso` cuando el precio cae por debajo de un factor del típico.
- Impacto: evita falsos positivos “oferta” por potencial error de carga, pero reduce recall en ofertas extremas sintéticas.
- Estado: **diseño intencional**, no bug.

### H2 (Menor) — Riesgo de interpretación externa de la unidad de precio
- Evidencia: configuración permite dos unidades (`habitacion_noche` o `formula_completa`) y en scorer se bifurca por `unidad_precio`.
- Impacto: si un integrador externo no respeta la unidad del artefacto, la decisión puede degradar.
- Mitigación: contrato API + ejemplos explícitos (ya parcialmente presente).

## Grupo 02

### H3 (Crítico) — Inconsistencia semántica potencial en unidad de precio
- Evidencia:
  - API exige `price_total` (total de estadía).
  - Servicio transforma a `price_std` dividiendo por noches, habitaciones y personas.
- Impacto: si en entrenamiento el campo base no era realmente “total”, la normalización induce sesgo sistemático y cae recall.
- Señal empírica alineada: en benchmark robusto, modo `multiply` produce recall 0.0 para `deal`; modo `direct` mejora a recall 0.389.
- Diagnóstico: **principal hipótesis causal** del bajo desempeño en detección de ofertas.

### H4 (Mayor) — Umbral de detección más permisivo en z pero aún insuficiente por escala
- Evidencia: `z_log_threshold = -1.0` y `min_discount = 0.2`.
- Impacto: aun con umbral relativamente menos estricto que G1, la escala de `price_std` queda alta en múltiples contextos y bloquea `deal`.
- Diagnóstico: umbral no compensa problema de escala/unidad.

### H5 (Menor) — Tensión documentación/implementación en nombres de unidad
- Evidencia: en datos y mensajes se alterna noción de “total” y “avg_price_average” con distintas interpretaciones.
- Impacto: dificulta comparabilidad justa entre grupos y facilita errores de integración.

---

## Hallazgos transversales

### T1 — Contratos API distintos (requiere adaptador)
- G1: endpoint y payload orientados a `price`.
- G2: endpoint y payload orientados a `price_total`.
- Impacto: benchmark directo sin adaptación es inválido.

### T2 — Evaluación corta previa (8 casos) no generalizable
- El set inicial es útil para smoke test, no para inferencia robusta.
- Impacto: riesgo de conclusiones docentes sobre-evidenciadas.

---

## Matriz de severidad

- Crítico: H3
- Mayor: H1, H4, T1, T2
- Menor: H2, H5

---

## Recomendaciones priorizadas

### P0 (inmediato)
1. Fijar y publicar contrato de unidad de precio inequívoco para cada API.
2. Agregar tests automáticos de consistencia de unidad (mismo caso en dos codificaciones).
3. Mantener benchmark robusto como evidencia obligatoria de release.

### P1 (siguiente iteración)
1. Recalibrar umbrales con validación ciega estratificada.
2. Reportar métricas por segmento (soporte/país/estadía/personas).
3. Añadir batería de robustez API (`invalid_input`, `insufficient_data`, etc.).

### P2 (mejora de producto)
1. Unificar contrato de evaluación inter-grupo para comparaciones futuras.
2. Publicar guía de integración con ejemplos positivos/negativos por unidad.

---

## Conclusión de auditoría

- No se detectaron fallas graves de infraestructura ni crashes en ejecución normal.
- El diferencial de desempeño observado se explica principalmente por decisiones de modelado y semántica de entrada, no por errores de servidor.
- Para devolución docente, el foco debe ponerse en generalización y consistencia de unidad de precio.
