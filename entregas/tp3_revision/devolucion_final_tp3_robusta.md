# Devolución final TP3 (validación robusta + revisión de código)

Fecha: 2026-10-21

## 1) Qué se ejecutó

Se ejecutó un proceso reproducible de validación robusta:

1. Construcción de benchmark ampliado desde 2025 (`robust_test_cases.csv`).
2. Evaluación de ambas APIs sobre el mismo set.
3. Doble evaluación de Grupo 02 por sensibilidad de unidad:
   - modo `multiply` (interpreta precio como base a multiplicar),
   - modo `direct` (envío directo).
4. Auditoría de código y supuestos metodológicos.

---

## 2) Dataset robusto generado

- Casos totales: **540**
- Casos etiquetados (para métricas principales): **450**
- Escenarios:
  - `synthetic_deal`: 180
  - `synthetic_no_deal`: 270
  - `synthetic_borderline`: 90 (excluidos de score principal)

Cobertura de segmentos:
- `stay_bucket`: 1, 2-3, 4-6, 7+
- `persons_bucket`: 1, 2, 3-4, 5+
- `country_bin`: US + top países + cola (`other`)
- `ctx_support`: de 30 a 149

---

## 3) Resultados globales

### Modo principal comparativo (`g2_price_mode = multiply`)

- **Grupo 01**
  - accuracy: 0.873
  - precision: 1.000
  - recall: 0.683
  - f1: 0.812
  - fpr: 0.000

- **Grupo 02**
  - accuracy: 0.600
  - recall: 0.000
  - f1: N/A (sin verdaderos positivos)
  - fpr: 0.000

### Sensibilidad de unidad para Grupo 02 (`g2_price_mode = direct`)

- **Grupo 02**
  - accuracy: 0.722
  - precision: 0.824
  - recall: 0.389
  - f1: 0.528
  - fpr: 0.056

Interpretación:
- El desempeño de Grupo 02 cambia drásticamente según codificación de precio.
- Esto confirma que la unidad de entrada es el factor más crítico de su performance.

---

## 4) Lectura por segmentos (resumen)

- Grupo 01 mantiene **cero falsos positivos** en todo el benchmark robusto.
- Grupo 01 pierde recall en ofertas sintéticas extremas por política conservadora (`sospechoso`).
- Grupo 02 mejora al usar modo `direct`, pero continúa con recall moderado-bajo en varios segmentos.
- La brecha en recall se mantiene en `country_bin=us` y `other`.

---

## 5) Causa probable de los resultados

## Grupo 01
- Funciona bien en precisión por regla robusta + umbral estricto.
- Falla en parte de `deal` extremos por diseño de seguridad anti error de carga.

## Grupo 02
- La principal causa del bajo recall en modo comparativo estándar es la escala de `price_std` inducida por la normalización.
- En modo alternativo (`direct`) recupera parte del recall, lo que refuerza hipótesis de inconsistencia de unidad.

---

## 6) Diagnóstico docente (qué está pasando)

1. **No es un problema de API caída ni de Docker**: ambos servicios funcionan.
2. **Sí es un problema de semántica + calibración**:
   - contrato de precio no homogéneo,
   - sensibilidad alta a cómo se codifica el input,
   - umbrales no robustos a ese desacople.
3. La evaluación corta inicial (8 casos) era insuficiente para generalizar.

---

## 7) Recomendaciones para devolución a estudiantes

## Grupo 01
- Fortalezas:
  - estabilidad operativa,
  - alta precisión,
  - buena interpretación de respuesta.
- Mejoras:
  - revisar política de `sospechoso` para no perder recall en ofertas extremas válidas.

## Grupo 02
- Fortalezas:
  - API clara y explicativa,
  - arquitectura de cascada bien estructurada.
- Mejoras críticas:
  1. cerrar definición única de unidad de precio (train + inferencia + docs),
  2. recalibrar umbrales tras alinear unidad,
  3. revalidar con benchmark robusto estratificado.

---

## 8) Veredicto técnico actual

- Ambos grupos: **aprobados técnicamente en ejecución**.
- En rendimiento robusto comparativo:
  - **Grupo 01** superior en detección de `deal` bajo este benchmark.
  - **Grupo 02** requiere corrección metodológica prioritaria para evitar subdetección.

---

## 9) Evidencia producida

- `plan_step_by_step_validacion_robusta.md`
- `robust_validation_tp3.py`
- `robust_test_cases.csv`
- `robust_api_results_multiply.csv`
- `robust_metrics_global_multiply.csv`
- `robust_metrics_by_segment_multiply.csv`
- `robust_api_results_direct.csv`
- `robust_metrics_global_direct.csv`
- `robust_metrics_by_segment_direct.csv`
- `auditoria_codigo_tp3.md`

Con esto la devolución queda trazable, reproducible y defendible con datos.
