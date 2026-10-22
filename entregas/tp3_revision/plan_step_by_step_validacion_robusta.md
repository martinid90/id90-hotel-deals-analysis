# Plan step-by-step para validación robusta TP3

Fecha: 2026-10-21

## Objetivo
Emitir una devolución completa y defendible con evidencia reproducible sobre:
1) funcionamiento técnico,
2) desempeño real del algoritmo,
3) capacidad de generalización,
4) riesgos metodológicos y errores potenciales de implementación.

---

## Paso 0 — Congelar alcance y artefactos

**Entregables de este proceso** (en esta carpeta):
- `robust_test_cases.csv` (dataset ampliado)
- `robust_api_results.csv` (predicción por caso y por grupo)
- `robust_metrics_global.csv` (métricas globales)
- `robust_metrics_by_segment.csv` (métricas por segmento)
- `auditoria_codigo_tp3.md` (hallazgos de revisión de código)
- `devolucion_final_tp3_robusta.md` (devolución final consolidada)

Criterio de trazabilidad: todo debe poder regenerarse con scripts.

---

## Paso 1 — Construir benchmark robusto con datos (sin tocar código de alumnos)

1. Tomar históricos 2025.
2. Crear anclas reales de búsqueda con contexto válido.
3. Estratificar por:
   - soporte del contexto (bajo/medio/alto),
   - duración de estadía,
   - país (top vs cola),
   - ocupación básica.
4. Inyectar factores de precio controlados sobre cada ancla.
5. Etiquetar por construcción:
   - `deal`: descuentos fuertes,
   - `no_deal`: base o caro,
   - `borderline`: zona gris (se excluye de métricas principales).

Resultado: dataset con suficiente tamaño para inferencia (no 8 casos).

---

## Paso 2 — Evaluar ambas APIs con el mismo dataset

1. Levantar ambos contenedores.
2. Ejecutar evaluación automática con adaptador de payload por grupo.
3. Guardar:
   - respuesta raw,
   - decisión normalizada,
   - errores/timeout,
   - métricas globales y por segmento.

Métricas mínimas:
- coverage,
- accuracy,
- precision,
- recall,
- f1,
- fpr,
- matriz de confusión.

---

## Paso 3 — Stress tests funcionales API

Agregar lote específico para:
- `invalid_input`,
- `invalid_price`,
- `insufficient_data`,
- payload incompleto/tipo inválido.

Objetivo: validar robustez de servicio, no solo performance.

---

## Paso 4 — Auditoría de código completa

Checklist por grupo:
1. contrato de entrada/salida API,
2. unidad de precio (consistencia train/inferencia),
3. riesgo de doble normalización,
4. fallback y soporte mínimo,
5. separación temporal train/test,
6. riesgo de leakage,
7. tratamiento de outliers,
8. umbrales y su interpretación,
9. manejo de errores,
10. reproducibilidad (scripts, seeds, artefactos).

Formato: hallazgo → evidencia de código → impacto → recomendación.

---

## Paso 5 — Explicar por qué funciona bien/mal

Conectar resultados de métricas con causa técnica:
- dónde detecta bien,
- dónde falla,
- si falla por sesgo de umbral, unidad, soporte o mapping,
- si hay tradeoff precisión vs recall.

---

## Paso 6 — Devolución final docente

Por grupo:
- fortalezas,
- debilidades críticas,
- prioridad de correcciones (P0/P1/P2),
- criterio de aprobación técnica y metodológica.

---

## Estado actual

- Plan definido ✅
- Siguiente acción: generar dataset robusto y correr benchmark ampliado.
