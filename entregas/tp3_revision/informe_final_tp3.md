# Informe final TP3 (comparativo)

Fecha: 2026-10-20

## Alcance
Se evaluaron técnicamente ambas entregas TP3 con los mismos criterios:
- build Docker,
- ejecución API,
- inferencia por endpoint,
- benchmark común sobre casos etiquetados (`deal`/`no_deal`).

## Resultado ejecutivo
- Ambos grupos: **aprobados técnicamente** para ejecución (build/run/API OK).
- Comparativo de desempeño en benchmark común:
  - **Grupo 01**: mejor capacidad de detección de ofertas en este set.
  - **Grupo 02**: comportamiento conservador, clasifica mayormente `no_deal`.

## Evidencia cuantitativa
Fuente: `comparativo_metricas.csv`.

- Grupo 01:
  - coverage: 1.0
  - accuracy: 0.875
  - precision: 1.0
  - recall: 0.667
  - f1: 0.8
- Grupo 02:
  - coverage: 1.0
  - accuracy: 0.625
  - recall: 0.0

## Hallazgo metodológico clave
Los contratos API y la semántica de precio difieren:
- Grupo 01: `POST /predict` con `price`.
- Grupo 02: `POST /evaluate` con `price_total` y normalización explícita por `nights`.

Para comparación justa fue necesario un adaptador común por grupo en el script de evaluación.

## Recomendaciones para cierre
1. Unificar contrato mínimo de inferencia (campos obligatorios y unidad de precio).
2. Publicar en README ejemplos positivos/negativos con unidad explícita.
3. Incorporar tests de regresión con casos borde (precio extremo, fallback geográfico, datos faltantes).
4. Reportar matriz de confusión y umbrales de decisión junto con métricas globales.

## Dictamen docente sugerido
- **Grupo 01**: buen nivel técnico y mejor desempeño relativo en detección de ofertas.
- **Grupo 02**: implementación sólida de servicio/API, pero requiere recalibración metodológica para mejorar sensibilidad a `deal`.
