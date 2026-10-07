**Grupo 2** · Jeremías Taran, Martín Gabriel Gómez, Jael Mataloni, Francisco Cisneros

---

# TP2 — Reporte Final: Curación de Mercado y Detección de Ofertas

## Pregunta de análisis

¿Qué proceso de transformación convierte las búsquedas hoteleras crudas en un conjunto de datos comparable, cómo se define operativamente un mercado con suficiente masa estadística y qué estadístico de detección identifica precios inusualmente bajos superando las limitaciones del z-score gaussiano lineal de referencia?

## Conclusión ejecutiva

1. Se estandarizó el precio a USD por habitación-noche-persona (`price_std`), eliminando distorsiones por tamaño de grupo o duración de viaje. El mapeo geográfico alcanzó una **cobertura del 69,9% en registros y del 82,3% en demanda ponderada**.
2. El mercado se definió operativamente como:
   $$\text{Mercado} = \text{destination\_final} \times \text{month} \times \text{week\_in\_month} \times \text{stay\_duration}$$
   De las 119.253 celdas resultantes, aquellas con $\text{demand\_weight} \ge 30$ concentran el **77,0%** de la demanda ponderada. No obstante, al evaluar la masa estadística por búsquedas únicas independientes ($\text{n\_records} \ge 30$), la cobertura confiable cae al **16,8%** (544 mercados). Esta marcada brecha demuestra que gran parte de la densidad observada proviene de repeticiones frecuentes (`count_repeated`), lo cual convierte a la cascada de rescate jerárquico en un componente central para el TP3.
3. Frente al z-score gaussiano lineal de referencia ($z < -1.0$, que detecta un 8,9% a un precio promedio de $15,81 USD), se comprobó que los hoteles de lujo inflan la desviación estándar ($\sigma$) en destinos heterogéneos, provocando falsos negativos. La transformación log-normal simetriza la distribución y eleva la detección al 14,2% a $16,33 USD (un 60% más de capturas con idéntico nivel de precio).
4. Se adoptó para TP3 un **detector híbrido**:
   $$\text{is\_deal} = (z_{\log} < -1.0) \;\land\; \left(1 - \frac{\text{price\_std}}{\text{mediana}_{\text{contexto}}} \ge 0.20\right)$$
   Este criterio detecta el **14,1%** de las observaciones a un precio medio de **$16,16 USD**, combinando significancia estadística proporcional con una exigencia mínima de relevancia económica real (al menos 20% de descuento sobre la tarifa típica del mercado).

## Segmentación propuesta

```text
Mercado = destination_final × month × week_in_month × stay_duration
```

- **`destination_final`**: mercado geográfico canónico; agrupa ciudades satélites con sus polos urbanos.
- **`month`**: controla la estacionalidad anual y períodos vacacionales.
- **`week_in_month`**: captura dinámicas intra-mes (quincenas y fines de semana largos).
- **`stay_duration`**: segmenta por tramos de duración (corta: 1-2 noches, media: 3-5, larga: >5), aislando el descuento no lineal por volumen.
- **`price_bucket`** (categoría proxy de hotel): se calcula mediante percentiles p25/p75 locales, pero **no** particiona el baseline para evitar fragmentar la muestra y prevenir circularidad metodológica.

## Evidencia principal

### 1. Cobertura del mapeo geográfico (muestra de 300.000 registros)

| Métrica | Total | Mapeadas | % Cobertura |
|---|---:|---:|---:|
| Filas de búsqueda | 299.765 | 209.613 | 69,9% |
| Demanda ponderada (`count_repeated`) | 2.180.093 | 1.793.554 | 82,3% |
| Geografías únicas (ciudad-estado-país) | 20.946 | 9.361 | 44,7% |

### 2. Categorías de hotel proxy (`price_bucket`)

| Categoría | Filas | % del total | Precio medio (`price_std`) |
|---|---:|---:|---:|
| Budget / Low | 76.141 | 25,6% | $14,26 USD |
| Mid-range / Medium | 141.054 | 47,4% | $38,51 USD |
| Premium / High | 80.168 | 27,0% | $122,00 USD |

### 3. Densidad de mercado y análisis de masa crítica

Sobre 119.253 mercados posibles, la representatividad varía drásticamente según la unidad de soporte evaluada:

| Criterio de masa crítica | Mercados que superan corte | % de mercados | Demanda cubierta | % de demanda |
|---|---:|---:|---:|---:|
| `demand_weight ≥ 30` (búsquedas ponderadas) | 10.974 | 9,2% | 1.670.930 | **77,0%** |
| `n_records ≥ 30` (búsquedas independientes únicas) | 544 | 0,5% | 363.952 | **16,8%** |

### 4. Dispersión relativa intra-mercado

En los mercados con masa crítica ($N \ge 30$), el Coeficiente de Variación ($CV = \sigma / \mu$) presenta una mediana de **0,58** (p25 = 0,44; p75 = 0,75), ratificando una heterogeneidad interna real entre polos turísticos de diversa dispersión tarifaria.

### 5. Comparativa de estadísticos de detección

Evaluación sobre 118.160 observaciones de búsqueda pertenecientes a mercados con soporte suficiente ($N \ge 30$):

| Método de detección | Observaciones marcadas | % Detectado | Precio medio detectado | Diagnóstico técnico |
|---|---:|---:|---:|---|
| **Detector Híbrido ($z_{\log} < -1.0$ y ahorro $\ge 20\%$) [ADOPTADO]** | **16.684** | **14,12%** | **$16,16 USD** | **Neutraliza el sesgo de lujo y asegura descuento económico real.** |
| Z-Score Log-Normal ($z_{\log} < -1.0$) | 16.837 | 14,25% | $16,33 USD | Mide desviaciones proporcionales; incluye casos con ahorro marginal en dólares. |
| Z-Score Gaussiano ($z < -1.0$) [Referencia] | 10.561 | 8,94% | $15,81 USD | Subestima ofertas: en plazas heterogéneas los hoteles de lujo inflan $\sigma$ (falsos negativos). |
| Z-Score Good Price ($z < -0.5$) | 37.107 | 31,40% | $24,84 USD | Tarifa competitiva general; no constituye anomalía estadística estricta. |
| Descuento $\ge 30\%$ sobre mediana | 30.083 | 25,46% | $21,18 USD | Umbral intuitivo pero rígido; no pondera la dispersión inherente a la plaza. |
| Percentil 10 contextual | 16.924 | 14,32% | $18,73 USD | Impone cuota fija artificial aun en mercados planos sin ofertas reales. |
| IQR inferior de Tukey ($Q_1 - 1,5 \times IQR$) | 1.080 | 0,91% | $24,43 USD | Baja sensibilidad: en distribuciones asimétricas la cerca cae bajo el soporte real. |

*Ejemplo empírico*: en destinos como Las Vegas, Miami o Cancún, una tarifa de $25 USD dentro de un contexto con $\mu = \$90$ y $\sigma = \$75$ arroja $z = (25 - 90)/75 = -0,87$ (clasificado apenas como "Good Price" por el modelo gaussiano). En escala logarítmica, la distancia proporcional resulta en $z_{\log} \approx -2,0$, reconociendo la oportunidad tarifaria real.

## Decisiones descartadas

1. **Percentil 10 como clasificador directo**: descartado porque fuerza una proporción constante de ofertas (10-14%) con independencia de la homogeneidad de la plaza.
2. **Cerca inferior de Tukey**: descartada por inoperante (0,9% de activación); la asimetría a derecha sitúa el corte formal fuera del dominio de precios factibles.
3. **Z-Score lineal no acotado como único criterio**: descartado por vulnerabilidad ante varianzas infladas por resorts premium.
4. **`price_bucket` como dimensión de baseline**: se descarta para particionar celdas para no multiplicar la fragmentación muestral y evitar circularidad analítica.

## Cobertura y confianza

Bajo el criterio de demanda agregada (`demand_weight ≥ 30`), el 77,0% del volumen transaccional queda respaldado. Sin embargo, el análisis de sensibilidad sin ponderar (`n_records ≥ 30`) evidencia que solo el 16,8% de la demanda cuenta con 30 búsquedas independientes.

Por consiguiente, la **cascada de rescate jerárquico** planificada para TP3 deja de ser una excepción para convertirse en la regla operativa primaria:
$$\text{Semana exacta} \;\longrightarrow\; \text{Mes completo} \;\longrightarrow\; \text{Destino global}$$

## Limitaciones

1. **Validez sobre muestra**: los resultados proceden de la muestra de 300.000 búsquedas (seed=42). Resta verificar su estabilidad sobre los 5,15 millones de filas completas.
2. **Pseudoreplicación en `demand_weight`**: un mercado puede aparentar solidez estadística con solo 1 o 2 búsquedas originales repetidas cientos de veces (`count_repeated` alto).
3. **Cola geográfica sin destino**: el 30,1% de las filas (17,7% de la demanda) no matchea contra el maestro geográfico y opera bajo `city` cruda como salvaguarda.
4. **Proxy circular de gama (`price_bucket`)**: construido a partir del precio observado por carencia de atributos de infraestructura (estrellas, servicios). No debe participar en simultáneo como feature predictiva y como criterio evaluador.
5. **Riesgo de circularidad en etiquetas para TP3**: la variable objetivo `is_deal` se construye determinísticamente a partir de `price_std`, $z_{\log}$ y mediana. Los modelos de Machine Learning deben formularse con variables contextuales exógenas para evitar la mera replicación trivial del umbral aritmético.

## Próximos pasos (TP3)

1. Entrenar modelos supervisados (LightGBM, XGBoost, Random Forest) empleando únicamente features de contexto (`day_of_week`, `month`, `stay_duration`, `price_bucket`, `destination_final`), evaluando su capacidad predictiva frente a la heurística estadística.
2. Implementar formalmente la cascada de rescate jerárquico para dar cobertura robusta al 23% - 83% de demanda situada en celdas de baja densidad.
3. Definir operativamente el umbral de activación del fallback (`n_records` vs `demand_weight`).

---

# TP1 — Cierre Corregido: Definición de Contexto y Homogeneidad de Precios

## Pregunta de análisis

¿Qué combinación de dimensiones genera grupos de búsquedas hoteleras lo suficientemente homogéneos como para que la comparación de precios dentro de cada grupo sea estadísticamente válida?

## Conclusión ejecutiva

El mercado comparable es la geografía canónica (`destination_final`). Sobre ella, la segmentación que mejor equilibra homogeneidad interna y soporte estadístico es:
$$\text{Contexto} = \text{destination\_final} \times \text{month} \times \text{week\_in\_month} \times \text{stay\_duration}$$

La evidencia empírica confirma que agregar estas dimensiones multiplica el ratio señal-ruido (SNR), preservando soporte suficiente en celdas confiables.

## Segmentación propuesta

| Dimensión | Rol en el contexto | Justificación técnica |
|---|---|---|
| `destination_final` | Base geográfica canónica | Homogeneiza plazas y unifica satélites urbanos; comparar entre destinos distintos carece de validez. |
| `month` | Estacionalidad temporal | Aísla variaciones climáticas y temporadas turísticas. |
| `week_in_month` | Dinámica de calendario | Capta efectos quincenales y cobro de salarios. |
| `stay_duration` | Control de duración | Corrige el descuento por volumen presente entre estadías de distinta extensión. |

## Evidencia principal

### 1. Signal-to-Noise Ratio (SNR) y soporte muestral por combinación de dimensiones

Evaluación sobre muestra representativa de 300.000 filas (seed=42) en destinos canónicos:

| Nivel de segmentación | SNR | Contextos generados | % Contextos confiables ($N \ge 30$) | % Demanda en contextos confiables |
|---|---:|---:|---:|---:|
| Solo Destino | 0,0603 | 1.890 | 69,4% | 99,9% |
| Destino + Mes | 0,1222 | 13.902 | 47,3% | 98,5% |
| Destino + Mes + Semana | 0,1912 | 38.268 | 34,8% | 95,4% |
| **Destino + Mes + Semana + Estadía** | **0,5384** | **68.487** | **28,5%** | **91,4%** |

*Interpretación*: la segmentación adoptada multiplica por 9 el SNR frente al destino aislado, manteniendo más del 91% del volumen de demanda en celdas con al menos 30 unidades de demanda ponderada.

### 2. Estabilidad interanual de patrones (2024 vs 2025)

- **Duración de estadía**: correlación de rangos $r \approx 1,000$.
- **Día de la semana**: correlación de perfiles $r \approx 1,000$.
- **Jerarquía de destinos principales**: correlación $r > 0,900$.

### 3. Cobertura y auditoría del mapping geográfico

- **69,9%** de cobertura en registros crudos y **82,3%** de la demanda ponderada (`count_repeated`).
- Registro explícito de trazabilidad (`match_level`) y preservación controlada de casos `no_match` (evitando imputaciones geográficas forzadas).

### 4. Correcciones metodológicas implementadas tras devolución docente

1. **Desagregación temporal sin checkout**: se corrigió la expansión de fechas para generar exactamente `nights` noches pagadas (del día de check-in al día previo a la salida), eliminando el cómputo erróneo del día de checkout.
2. **Convención de días de la semana**: se unificó la nomenclatura de pandas (`0 = Lunes`, ..., `6 = Domingo`), subsanando el desplazamiento de etiquetas de la entrega original.
3. **Unidades de análisis explícitas**: discriminación rigurosa entre `demand_weight` (suma de `count_repeated`) y `n_records` (registros no ponderados).
4. **Muestreo reproducible**: fijación estricta de semilla (`seed=42`) para viabilizar la trazabilidad de resultados.

> El detalle técnico completo de cada cambio aplicado a los scripts y notebooks originales se encuentra documentado en el archivo [`INFORME_CORRECCIONES_TP1.md`](INFORME_CORRECCIONES_TP1.md).

## Decisiones descartadas

- `country`: agregación excesiva que mezcla polos disímiles.
- `day_of_week`: introduce dispersión muestral sin un incremento generalizado de homogeneidad.
- `avg_hotel_count`: variable de oferta hotelera, no dimensión de segmentación.
- `count_repeated`: peso de demanda, no variable de partición.

## Cobertura y confianza

Sobre la base completa de datos (5,16 millones de registros), la segmentación propuesta conforma ~707.000 contextos, de los cuales 157.705 superan el umbral $N \ge 30$, concentrando el **96,3%** de la demanda agregada total.

## Limitaciones reconocidas

1. **Proxy `price_bucket`**: introduce riesgo de endogeneidad analítica al estratificar por percentiles del propio precio observado ante ausencia de metadatos hoteleros de calidad.
2. **Remanente geográfico sin mapeo**: ~18% de la demanda persiste sin asignación a destino canónico por corresponder a distritos o variantes toponímicas no consolidadas.
