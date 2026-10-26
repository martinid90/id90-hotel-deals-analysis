**Grupo 2** · Jeremías Taran, Martín Gabriel Gómez, Jael Mataloni, Francisco Cisneros

---

# TP3 — Reporte final: algoritmo de detección de ofertas

## Pregunta

Dado el precio de una búsqueda hotelera y la historia de su mercado, ¿es una oferta? ¿Qué algoritmo lo detecta mejor, con qué cobertura, y cómo se evalúa sin una etiqueta externa?

## Conclusión ejecutiva

1. **Algoritmo elegido: detector híbrido con cascada de fallback.**
   - Marca oferta si $z_{\log} < -1$ y el descuento sobre la mediana histórica del contexto es ≥ 20%.
   - El contexto es `destino × mes × semana × estadía`. Si no hay 30 búsquedas independientes, la cascada baja hasta nivel país.
   - **Resultado en 2025, con baselines de 2024:** F1 0,764, precision 0,725, recall 0,806, FPR 5,4%, cobertura operativa 98,9%.
2. **Algoritmo ML** Un HistGradientBoosting con features exógenas (sin bucket, sin mediana, sin z) logra F1 0,770. Se prefiere la regla porque es explicable, solo necesita los campos de la query y se mantiene recalculando medianas.
3. **La evaluación in-period es engañosa.** En un split aleatorio dentro de 2024 el mismo detector da F1 0,919. La caída a 0,764 en 2025 la explica la **deriva de precios entre años**, que es la principal fuente de error.
4. **Un −30% no es oferta en este mercado.** Con la dispersión real (los mercados mezclan categorías de hotel), recién un descuento del 60% o más es consistentemente anómalo. Es el hallazgo más relevante para discutir con negocio.
5. **Cerramos los pendientes del TP2:**
   - `price_bucket` queda fuera del modelo. Además, el análisis muestra que reproduce casi la etiqueta (0,1% de ofertas en `high`).
   - Soporte = 30 `n_records`.
   - El corte de outliers p99.9 queda cerrado: no mueve las métricas.
   - Hay fallback explícito en todos los casos.
6. **Riesgo principal abierto: la unidad del precio.** La evidencia indica que `avg_price_average` es tarifa por noche, pero la fórmula heredada divide además por noches. Eso sesga hacia "oferta" las estadías largas: 26,3% de ofertas contra 12,5% en estadías cortas. Mantuvimos la fórmula por consistencia con la mentoría y lo dejamos documentado en *Limitaciones*.

## Diseño de la evaluación

| Componente | Decisión |
|---|---|
| Datos | 5.145.974 búsquedas válidas, el 99,76% de las crudas. Se agregó un piso de 1 USD por habitación-noche-persona para filtrar errores. |
| Split | **Temporal:** train = check-in 2024 (2,51 M), test = check-in 2025 (2,63 M). Control: aleatorio 80/20 dentro de 2024. |
| Etiqueta | Regla híbrida sobre la **distribución realizada de 2025**, que los detectores no ven. Tiene etiqueta el 99,1% del test; la prevalencia es 15,0%. |
| Anti-leakage | Outliers, baselines, encoders y umbral del ML se ajustan solo en 2024. `price_bucket` no es feature ni dimensión. |
| Test set compartido | 3.600 búsquedas reales estratificadas (destino × estadía × etiqueta), 2.400 sintéticas (8 factores de precio) y 11 casos borde. Va en formato de query de la API. |
| Métricas | Precision y FPR como prioridad (un falso positivo daña la confianza), F1 para seleccionar, cobertura como restricción y accuracy como referencia. |

## Comparación de algoritmos (test temporal 2025)

| Algoritmo | Precision | Recall | F1 | FPR | Cobertura | F1 ponderado por demanda |
|---|---:|---:|---:|---:|---:|---:|
| A Naive aleatorio | 0,151 | 0,151 | 0,151 | 0,150 | 100% | 0,088 |
| B Naive mediana −20% | 0,375 | 0,965 | 0,540 | 0,285 | 99,8% | 0,325 |
| C Z-score gaussiano | 0,783 | 0,461 | 0,580 | 0,023 | 99,8% | 0,540 |
| D Percentil 10 | 0,760 | 0,718 | 0,738 | 0,040 | 99,8% | 0,673 |
| **E Híbrido + cascada** | **0,725** | **0,806** | **0,764** | **0,054** | **99,8%** | **0,697** |
| F HistGradientBoosting | 0,756 | 0,785 | 0,770 | 0,045 | 100% | 0,736 |
| G Random Forest | 0,713 | 0,743 | 0,728 | 0,053 | 100% | 0,692 |

## Casos controlados (sintéticos)

Porcentaje de búsquedas marcadas como oferta cuando el precio se fija en *factor × mediana del mercado 2025*:

| Factor | 0,3 | 0,4 | 0,5 | 0,7 | 0,85 | 1,0 | 1,3 | 1,5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Verdad (definición) | 98% | 84% | 44% | 3% | 0% | 0% | 0% | 0% |
| E Híbrido | 89% | 76% | 49% | 9% | 3% | 2% | 0% | 0% |
| F HistGB | 90% | 71% | 40% | 10% | 4% | 2% | 1% | 0% |
| B Mediana −20% | 99% | 96% | 92% | 73% | 39% | **15%** | 5% | 2% |

- E y F siguen la curva de la definición. Ver en carpeta Figuras
- B marca el 15% de los precios **iguales** a la mediana 2025: el mercado se movió respecto de la historia.

A través de la API, el test set compartido da:
- **Bloque real:** F1 0,860, precision 0,918, FPR 7,2%. Está balanceado 50/50, así que estos números no se comparan con los poblacionales.
- **Bloque sintético:** F1 0,813.
- **Casos borde:** se resuelven todos con la decisión esperada (fallback a país, `insufficient_data`, `invalid_price`, `invalid_input`).

## Análisis de errores

| Hallazgo | Evidencia |
|---|---|
| Los errores vienen de la **deriva del mercado**, no de casos cerca del umbral | En los falsos positivos el mercado 2025 se abarató un 20% (mediana); en los falsos negativos se encareció un 25% |
| Mejor en destinos principales | F1 0,850 en el top 50, contra ~0,735 en la cola y en las ciudades sin mapeo |
| Los fallbacks que mezclan estadías generan más FP | FPR 12,4% en L3 (destino × mes) y 10,8% en L5 (destino), contra 4,0% en L1 |
| Fin de año más difícil | El recall cae de ~0,83 a 0,70 en diciembre |
| `price_bucket` ≈ etiqueta | Ofertas: 0,1% en `high` contra 46% en `low`. Usarlo como feature sería leakage. |

## Sensibilidad

| Variante | F1 | Precision | Cobertura | Lectura |
|---|---:|---:|---:|---|
| Soporte ≥ 10 / 30 / 50 / 100 | 0,726 / **0,764** / 0,757 / 0,732 | 0,683 / 0,725 / 0,720 / 0,694 | 100 / 99,8 / 99,6 / 98,9% | 30 es el mejor punto |
| `demand_weight ≥ 30` | 0,736 | 0,691 | 100% | Contar repeticiones infla el soporte |
| Sin fallback (solo L1) | 0,812 | 0,764 | 44,6% | Preciso pero pierde mucha cobertura |
| Sin semana del mes | **0,775** | **0,745** | 99,8% | La semana sobre-segmenta |
| Solo destino | 0,644 | 0,641 | 94,3% | Mes y estadía son necesarios |
| $z_{\log}$ < −1,25 | 0,742 | 0,839 | 99,8% | Modo conservador: FPR 2,3% |
| Descuento 10% / 20% / 30% | 0,764 / 0,764 / 0,764 | — | — | La condición casi nunca se activa |
| p99 vs sin corte | 0,764 … 0,763 | — | — | p99.9 queda como definitivo no hay cambio |

## Decisiones descartadas

- **Z-score gaussiano:** detecta menos de la mitad de las ofertas.
- **Percentil 10:** impone una cuota fija
- **Mediana −20%:** FPR del 28%.
- **Random Forest:** peor que el boosting y poco sensible al precio.
- **HistGradientBoosting en producción:** rinde parecido, pero no es explicable y necesita `avg_hotel_count`, que no viene en la query. Queda como alternativa

## Limitaciones

**Riesgo principal: unidad del precio.** La evidencia indica que `avg_price_average` es una tarifa por noche, no el total de la estadía. En búsquedas de 2 adultos y 1 habitación:

| Noches | 1 | 2 | 3 | 5 | 7 |
|---|---:|---:|---:|---:|---:|
| Mediana de `avg_price_average` (USD) | 138 | 153 | 177 | 193 | 208 |

La fórmula de `price_std` heredada del TP2 (`precio / (noches × hab × personas)`) igual divide por las noches. Eso abarata artificialmente las estadías largas: la tasa de ofertas es del 26,3% con más de 5 noches, contra 12,5% en estadías cortas. `stay_duration` en el contexto lo atenúa, pero no lo elimina dentro de cada tramo.

Se mantuvo la fórmula por consistencia con la definición acordada en la mentoría. Si se confirma que el campo es por noche, la corrección es `price_std = precio / (habitaciones × personas)`.

**Otras limitaciones:**

1. **Sin categoría de hotel.** La dispersión de cada mercado mezcla hoteles económicos y de lujo.
2. **Deriva interanual.** Hace falta una ventana móvil para los baselines y monitorear la tasa de marcado.
3. **La API sirve baselines de 2024.** Así el test set es reevaluable

## Trabajo futuro

1. Confirmar la unidad de `avg_price_average` y, si es tarifa por noche, corregir `price_std`.
2. Baselines con ventana móvil de 12 meses.
3. Incorporar la categoría real del hotel.
4. Calibrar el umbral de $z_{\log}$ con experto en el mercado (precision contra recall).

