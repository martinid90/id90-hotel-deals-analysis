# TP2 — Curación de datos y definición de mercado

**Diplomatura en Ciencia de Datos · Mentoría ID90Travel 2026**
**Fecha de entrega:** 04/09

---

## 1. Contenido

El TP2 entrega el dataset curado y las reglas del detector de ofertas del TP3. Dos partes:

1. **Curación**:
   - **Limpieza**: se descartaron 235 búsquedas con 0 personas, noches inconsistentes ($\le 0$ o $> 30$), 0 habitaciones o precios inválidos.
   - **Normalización**:
     $$\text{price\_std} = \frac{\text{avg\_price\_average}}{\text{noches} \times \text{habitaciones} \times (\text{adultos} + \text{niños})}$$
   - **Winsorización**: percentil 99.9 ($1.416 USD por habitación-noche-persona) para que las tarifas atípicas no deformen los desvíos.
   - **Features temporales**: día de check-in (`day_of_week`), mes (`month`), semana del mes (`week_in_month`), año (`year`) y duración de estadía (`stay_duration`: corta 1-2n, media 3-5n, larga >5n).
   - **Mapping geográfico**: ~26.000 nombres crudos agrupados en destinos canónicos con `destination_with_nearest.csv`. Cubre el **82.3% de la demanda**.
   - **Categoría de hotel proxy (`price_bucket`)**: Económico (`low`), Medio (`medium`) y Premium (`high`) según cuartiles de precio por destino.

2. **Análisis**:
   - **Definición de mercado**: $\text{Mercado} = \text{destination\_final} \times \text{month} \times \text{week\_in\_month} \times \text{stay\_duration}$.
   - Retiene el **77% de la demanda** en celdas con $N \ge 30$ observaciones ponderadas.
   - **Distribución de precios**: asimétrica a derecha — la mayoría paga precios moderados y una cola de tarifas premium estira el promedio.
   - **Comparativa de detectores**: cinco alternativas contra el Z-score lineal del docente, evaluadas solo en mercados con $N \ge 30$. De ahí sale el **detector híbrido** del TP3.

---

## 2. Definición de mercado

$$\mathbf{\text{Mercado}} = \mathbf{\text{destination\_final} \times \text{month} \times \text{week\_in\_month} \times \text{stay\_duration}}$$

### Por qué esta segmentación:

- **Destino canónico**: junta cada ciudad satélite con su polo y evita fragmentar la muestra.
- **Mes**: aisla la estacionalidad climática y los picos de vacaciones (enero/julio/diciembre).
- **Semana del mes**: captura quincenas de cobro y fines de semana largos.
- **Duración de estadía**: las cadenas aplican descuentos por volumen; comparar 1 noche contra 14 distorsiona el precio diario.
- **Masa estadística y sensibilidad**: bajo demanda ponderada (`demand_weight ≥ 30`), las celdas confiables concentran el **77.0%** del volumen (10.974 mercados). Bajo búsquedas independientes sin ponderar (`n_records ≥ 30`), la cobertura cae al **16.8%** (544 mercados), ratificando la centralidad de la cascada de rescate jerárquico para TP3.

---

## 3. Auditoría y curación

### Embudo de datos

| Etapa | Registros | % Retenido |
|---|---|---|
| Datos crudos (`sample_data_300k.csv.gz`) | 300.000 | 100.00% |
| Denominadores válidos y noches $\le 30$ | 299.958 | 99.98% |
| Precios válidos ($> 0$) y winsorizados | 299.765 | 99.92% |

### Auditoría residual: cero valores inválidos

- `precio_std <= 0`: 0
- `noches <= 0`: 0
- `habitaciones <= 0`: 0
- `ocupacion <= 0`: 0
- `noches > 30`: 0

### Cobertura del mapping geográfico

- **69.9%** de las filas mapeadas a destino canónico.
- **82.3%** de la demanda ponderada cubierta.
- Las ciudades no mapeadas (30.1% de filas, 17.7% de demanda) se conservan con su nombre crudo para no perder registros.

### Categorías de hotel proxy (`price_bucket`)

- **Budget / Económico (`low`)**: 25.6% de las búsquedas (precio promedio: $14.26 USD).
- **Mid-Range / Estándar (`medium`)**: 47.4% de las búsquedas (precio promedio: $38.51 USD).
- **Premium / Lujo (`high`)**: 27.0% de las búsquedas (precio promedio: $122.00 USD).

---

## 4. Comparativa de detectores

118.160 observaciones de mercados con $N \ge 30$. Con 1 o 2 registros los percentiles colapsan y los z-scores dependen de la salvaguarda: medirían ruido, no detección.

| Método | Filas marcadas | % Detectado | Precio promedio (USD) | Diagnóstico |
|---|---|---|---|---|
| **Detector Híbrido ($z_{\log} < -1.0$ & Ahorro $\ge 20\%$) [ADOPTADO]** | **16.684** | **14.12%** | **$16.16** | **Neutraliza la cola de lujo y exige un ahorro tangible.** |
| Z-Score Log-Normal ($z_{\log} < -1.0$) [Alternativa 1] | 16.837 | 14.25% | $16.33 | Simetriza la distribución, pero deja pasar un pequeño grupo sin descuento real. |
| Z-Score Gaussiano ($z < -1.0$) [Docente] | 10.561 | 8.94% | $15.81 | Subestima ofertas: en plazas heterogéneas los hoteles de lujo inflan $\sigma$ y causan falsos negativos. |
| Z-Score Good Price ($z < -0.5$) [Docente] | 37.107 | 31.40% | $24.84 | Marca precios buenos, no necesariamente ofertas. |
| Descuento $\ge 30\%$ s/ Mediana [Alternativa 2] | 30.083 | 25.46% | $21.18 | Se entiende fácil, pero ignora la dispersión del mercado. |
| Percentil 10 contextual | 16.924 | 14.32% | $18.73 | Fuerza una cuota fija aun en mercados homogéneos sin ofertas reales. |
| IQR inferior ($Q_1 - 1.5 \cdot IQR$) | 1.080 | 0.91% | $24.43 | Casi no se activa: con sesgo positivo la cerca inferior cae por debajo del precio mínimo del mercado. |

---

## 5. Criterio de detección adoptado para TP3

El detector adoptado (ground truth del TP3):

$$\mathbf{\text{is\_deal}} = (z_{\log} < -1.0) \;\land\; \left(1 - \frac{\text{price\_std}}{\text{mediana}_{\text{contexto}}} \ge 0.20\right)$$

### Fundamentación técnica:

1. **Frente al Z-Score Gaussiano lineal de referencia:**
   En Las Vegas o Cancún, hoteles de $800 inflan $\sigma$ y una tarifa de $25 da $z = -0.87$: la oferta se pierde. En logaritmo la dispersión se mide en proporciones y el sesgo desaparece: detecta 60% más ofertas (14.2% contra 8.9%) al mismo precio medio.
2. **Frente al Percentil 10:**
   El percentil fuerza una cuota fija en cualquier destino, incluso en plazas de tarifas planas donde no hay ninguna oportunidad real.
3. **La cota sobre la mediana ($\ge 20\%$):**
   En mercados de tarifas casi fijas, $39 en vez de $41 da z significativo por $2 de ahorro. La cota exige un ahorro tangible y cuesta 0.1 puntos de detección.
4. **Uso en el TP3:**
   - Esta regla define la etiqueta binaria `is_deal`.
   - Se entrenan clasificadores (LightGBM, XGBoost, Random Forest) con las variables de contexto (`day_of_week`, `month`, `stay_duration`, `price_bucket`, `destination_final`) para comparar el ML contra la regla estadística.
   - En celdas con $N < 30$ se mantiene la cascada de rescate:
     $$\text{Semana exacta} \;\longrightarrow\; \text{Mes completo} \;\longrightarrow\; \text{Destino global}$$

---

## 6. Archivos del paquete

| Archivo | Rol |
|---|---|
| `reporte_final.md` | Síntesis ejecutiva de TP2 y cierre corregido de TP1 (SNR, métricas y decisiones). |
| `INFORME_CORRECCIONES_TP1.md` | Informe detallado de correcciones metodológicas de TP1 tras devolución docente. |
| `TP2_curacion_mercado.ipynb` | Notebook ejecutable: código, salidas, gráficos y tablas (ya ejecutado). |
| `TP2_curacion_mercado.py` | Gemelo Jupytext (`py:percent`), sincronizado con el `.ipynb`. |
| `config.py` | Umbrales, rutas y reglas del análisis. |
| `auxiliary_functions.py` | Funciones de curación, mapping y estadísticos. |
| `data/sample_data_300k.csv.gz` | Muestra aleatoria de 300.000 búsquedas (seed=42). |
| `data/destination_with_nearest.csv` | Mapping de ciudades crudas a destinos canónicos. |
| `README.md` | Este informe técnico general. |

---

## 7. Cómo ejecutar

Requiere Python 3.10 o superior.

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2a. Abrir el notebook y correrlo celda por celda
jupyter notebook TP2_curacion_mercado.ipynb

# 2b. O ejecutar el análisis completo desde la terminal
python TP2_curacion_mercado.py
```

Todo se corre desde esta carpeta. Tarda unos 2 minutos sobre la muestra incluida. Sin internet ni credenciales: lo que usa está en `data/`.

Para los 5.1 millones de registros completos (no incluidos por tamaño): copiar ambos CSV en `data/` y correr con `USE_FULL_HISTORICALS=1`.
