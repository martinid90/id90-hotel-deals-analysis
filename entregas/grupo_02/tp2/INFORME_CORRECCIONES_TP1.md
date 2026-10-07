# Informe de Correcciones TP1 → TP1_CORREGIDO

## 1. Objetivo

Este documento resume las correcciones aplicadas a la entrega de TP1 del **Grupo 2** a partir de la devolución del docente, y compara los resultados del pipeline original contra la versión corregida.

---

## 2. Correcciones aplicadas

### 2.0 Criterios generales para ambos grupos

Aplicamos estas correcciones que el docente pidió a ambos grupos:

- `reporte_final.md` es una síntesis ejecutiva, no una copia del notebook.
- `README.md` indica: notebook principal, datos, instalación, ejecución, supuestos, conclusión y limitaciones.
- El mapping es reproducible y auditado mediante `match_level`.
- La unidad de análisis es: fila original → noche pagada → contexto agregado, con `count_repeated` como peso.
- `price_bucket` es un proxy de categoría hotelera y una limitación aceptable.

### 2.1 Expansión temporal: ahora genera exactamente `nights` noches pagadas

**Qué hacía el original:**

```python
df['n_days'] = (df['date_end'] - df['date_start']).dt.days + 1
```

Como en los datos `date_end - date_start == nights`, esta fórmula generaba `nights + 1` filas, incluyendo el checkout como si fuera una noche pagada.

**Ejemplo:**

```text
date_start = 2024-03-26
date_end   = 2024-03-30
nights     = 4
```

- Original generaba 5 filas: 26, 27, 28, 29, 30.
- Corregido genera 4 filas: 26, 27, 28, 29 (el 30 es checkout).

**Qué se cambió:**

```python
repeat_counts = df['nights'].where(df['nights'] > 0, 1).astype(int).values
offsets = np.concatenate([np.arange(n) for n in repeat_counts])
df_expanded['date'] = df_expanded['date_start'].values + pd.to_timedelta(offsets, unit='D')
```

Archivo modificado: `auxiliary_functions.py`, función `expand_dates_dataframe`.

---

### 2.2 Días de la semana corregidos

**Qué hacía el original:**

```python
df['day_of_week'] = df['date_start'].dt.dayofweek
dias_nombre = {0: 'Dom', 1: 'Lun', 2: 'Mar', 3: 'Mié', 4: 'Jue', 5: 'Vie', 6: 'Sáb'}
```

En pandas `dt.dayofweek` usa `0 = Lunes`, `6 = Domingo`, por lo que todas las etiquetas quedaban corridas.

**Qué se cambió:**

```python
dias_nombre = {0: 'Lun', 1: 'Mar', 2: 'Mié', 3: 'Jue', 4: 'Vie', 5: 'Sáb', 6: 'Dom'}
```

Archivo modificado: `TP1_exploracion_mercado.ipynb`.

---

### 2.3 Unidad de análisis explicitada: `demand_weight`, `n_records`, `count_obs`

**Qué hacía el original:**

- `count_obs` era la suma de `count_repeated` (demanda ponderada).
- `count_records` era el conteo de filas, pero su nombre no dejaba claro que representaba.

**Problema:** cuando se usa `N >= 30` como criterio de confianza, no quedaba claro si eran 30 filas reales, 30 noches o 30 unidades de demanda ponderada.

**Qué se cambió:**

En `calculate_baselines` se separaron explícitamente:

| Columna | Significado |
|---|---|
| `demand_weight` | Suma de `count_repeated` (demanda agregada real) |
| `n_records` | Cantidad de filas/noches desagregadas |
| `count_obs` | Alias de `demand_weight` mantenido por retrocompatibilidad |

Archivo modificado: `auxiliary_functions.py`, función `calculate_baselines`.

---

### 2.4 Mapping con trazabilidad (`match_level`)

**Qué hacía el original:**

La función `apply_destination_mapping` aplicaba una cascada de matching pero no registraba qué nivel funcionó para cada geografía.

**Qué se cambió:**

Se agregó la columna `match_level` con los valores:

- `state_code_city`: país + código de estado + ciudad
- `state_name_city`: país + nombre de estado + ciudad
- `country_city`: país + ciudad
- `country_city_tuple`: tupla (país, ciudad) en catálogo
- `no_match`: sin match, fallback a ciudad cruda

Archivo modificado: `auxiliary_functions.py`, función `apply_destination_mapping`.

---

### 2.5 Pipeline: `nights` y `match_level` se conservan hasta los baselines

Se actualizó `pipeline_build_baselines.py` para que las columnas `nights` y `match_level` lleguen a la etapa de expansión y agregación.

Archivo modificado: `pipeline_build_baselines.py`.

---

## 3. Resultados: comparación original vs corregido

Ambos pipelines se ejecutaron sobre el dataset completo (2024 + 2025): **5,158,190 filas originales**.

### 3.1 Baselines generados

| Métrica | Original | Corregido | Diferencia |
|---|---|---|---|
| Contextos totales | 741,600 | 673,030 | -68,570 (-9.25%) |
| Contextos de alta confianza (N≥30) | 201,235 (27.1%) | 157,705 (23.4%) | -43,530 (-3.7 pp) |
| Demanda total en baselines | 134,867,827 | 97,984,772 | -36,883,055 (-27.35%) |
| Demanda en contextos de alta confianza | 130,503,914 (96.8%) | 94,335,501 (96.3%) | -0.5 pp |

### 3.2 Observaciones expandidas

| Pipeline | Registros antes de expandir | Observaciones después de expandir |
|---|---|---|
| Original | 5,074,435 | No loggueado directamente, pero la demanda total indica aprox. 21.3M noches |
| Corregido | 5,070,963 | **16,441,972** noches pagadas |

La diferencia se explica porque el original contaba el checkout como noche adicional, inflando la demanda ponderada y el número de observaciones por contexto.

### 3.3 Estadísticas de precios en contextos de alta confianza

| Métrica | Original | Corregido |
|---|---|---|
| `mean_price_std` (media) | 47.41 | 43.49 |
| `mean_price_std` (mediana) | 28.59 | 26.45 |
| `std_price_std` (media) | 21.87 | 18.72 |
| `std_price_std` (mediana) | 7.17 | 6.98 |

La reducción en las medias y medianas es consistente con eliminar la noche de checkout y aplicar la política de outliers.

### 3.4 Calidad de datos

| Métrica | Original | Corregido |
|---|---|---|
| Mínimos negativos en `min_price_std` | 1,572 | **0** |
| Percentil 99 de `max_price_std` | 14,406.98 | 13,950.69 |

La corrección temporal y la política de outliers eliminaron los precios normalizados negativos y redujeron los valores extremos.

### 3.5 Diferencias en contextos comunes

| Variable | Media diff | Mediana diff | % con diff absoluta > 5% |
|---|---|---|---|
| `mean_price_std` | -1.81 | 0.00 | 11.9% |
| `std_price_std` | -1.80 | 0.00 | 14.4% |

La mayoría de los contextos comunes no cambia en su mediana, pero aproximadamente 1 de cada 7 contextos tiene una diferencia material en media o desvío.

### 3.6 SNR con soporte de datos

Se calculó el Signal-to-Noise Ratio para distintas segmentaciones, acompañado del porcentaje de contextos confiables (N≥30 unidades de demanda ponderada) y del porcentaje de demanda que queda en esos contextos.

| Segmentación | SNR | Contextos | % Contextos confiables | % Demanda confiable |
|---|---|---|---|---|
| Solo Destino | 0.0603 | 1.890 | 69,4% | 99,9% |
| Destino + Mes | 0.1222 | 13.902 | 47,3% | 98,5% |
| Destino + Mes + Semana | 0.1912 | 38.268 | 34,8% | 95,4% |
| Destino + Mes + Semana + Estadía | 0.5384 | 68.487 | 28,5% | 91,4% |

*Valores calculados sobre una muestra representativa de 300.000 filas originales (semilla 42), usando solo destinos canónicos mapeados.*

**Lectura:** agregar `month`, `week_in_month` y `stay_duration` aumenta fuertemente el SNR, pero fragmenta los datos. La segmentación propuesta conserva más del 90% de la demanda en contextos confiables.

---

## 4. Cobertura del mapping (`match_level`)

Con el pretratamiento del docente integrado, la cobertura sobre el dataset completo fue:

| `match_level` | Filas | % Filas | Demanda | % Demanda |
|---|---|---|---|---|
| `cc_state_code_city` | 1,726,296 | 33.47% | 17,430,867 | 46.90% |
| `cc_country_city` | 1,467,903 | 28.46% | 9,985,016 | 26.87% |
| `no_match` | 1,599,527 | 31.01% | 7,250,841 | 19.51% |
| `non_us_state_as_place` | 228,126 | 4.42% | 918,793 | 2.47% |
| `cc_state_name_city` | 107,542 | 2.08% | 1,261,913 | 3.40% |
| `usa_alias_state_code_city` | 16,854 | 0.33% | 192,935 | 0.52% |
| `cc_cdp_state_code_city` | 11,942 | 0.23% | 126,707 | 0.34% |
| **Total mapeado** | **3,558,663** | **69.0%** | **29,916,231** | **80.5%** |

**Lectura:**

- El **69.0%** de las filas y el **80.5%** de la demanda quedan mapeadas a un destino canónico.
- El **31.0%** de filas sin match representa un **19.5%** de la demanda; son principalmente barrios, distritos, CDP, territorios o nombres alternativos.
- Estos números coinciden con los reportados por el docente usando el pretratamiento recomendado.

---

## 5. Interpretación de las diferencias

1. **La corrección temporal es la más impactante.** Eliminamos la noche ficticia del checkout. Por eso la demanda ponderada baja un 27%.

2. **Menos contextos alcanzan alta confianza.** Al tener menos observaciones por contexto, baja el porcentaje de contextos con `N >= 30` de 27.1% a 23.5%. Esto es un efecto real de la corrección, no un error.

3. **Las medias y desvíos de precios bajan levemente.** Eliminar la noche de checkout remueve observaciones que antes sobrepesaban las estadías largas.

4. **El mapping recupera el 80,5% de la demanda**, pero el 19,5% restante sigue sin mapear. Esa cola son barrios, distritos, CDP y territorios.

---

## 6. Correcciones realizadas en esta versión

### 6.1 Criterios generales para ambos grupos

| # | Corrección | Estado | Archivo modificado |
|---|---|---|---|
| 1 | `reporte_final.md` como síntesis ejecutiva, no copia del notebook | ✅ | `reporte_final.md` |
| 2 | README con notebook principal, datos, instalación, ejecución, supuestos, conclusiones y limitaciones | ✅ | `README.md` |
| 3 | Mapeo reproducible y auditado con `match_level` | ✅ | `auxiliary_functions.py` |
| 4 | Unidad de análisis explicitada (fila → noche → contexto) | ✅ | `auxiliary_functions.py`, notebook |
| 5 | `count_repeated` como peso de demanda | ✅ | `auxiliary_functions.py` |
| 6 | `price_bucket` documentado como proxy y limitación aceptable | ✅ | `reporte_final.md`, notebook |
| 7 | Fecha de checkout no contada como noche pagada | ✅ | `auxiliary_functions.py` |
| 8 | Cobertura de mapping reportada por filas, demanda y geografía única | ✅ | informe, notebook |

### 6.2 Correcciones específicas del Grupo 2

| # | Corrección | Estado | Archivo modificado |
|---|---|---|---|
| 1 | Una sola fuente de datos determinista para conclusiones (ambos años o sample con semilla) | ✅ | `TP1_exploracion_mercado.ipynb` |
| 2 | Diccionario de días de semana corregido | ✅ | `TP1_exploracion_mercado.ipynb` |
| 3 | Alineación entre check-in del notebook y noches pagadas del pipeline | ✅ | `auxiliary_functions.py`, notebook |
| 4 | Registros, demanda ponderada y noches separados (`n_records`, `demand_weight`) | ✅ | `auxiliary_functions.py` |
| 5 | SNR con soporte de datos | ✅ | notebook, `reporte_final.md` |
| 6 | Política explícita de outliers | ✅ | `auxiliary_functions.py` |

### 6.3 Comparación con y sin `price_bucket`

| Métrica | Sin `price_bucket` | Con `price_bucket` |
|---|---|---|
| Contextos totales | 365.989 | 673.030 |
| Alta confianza (N≥30) | 101.880 (27,8%) | 157.705 (23,4%) |
| Demanda total | 99.975.146 | 97.984.772 |
| `mean_price_std` mediana (alta conf.) | 32,28 | 26,45 |
| `std_price_std` mediana (alta conf.) | 22,29 | 6,98 |

Con `price_bucket` se fragmenta más (más contextos) pero se reduce fuertemente la varianza interna, lo cual justifica su uso como proxy de categoría siempre que se declare el riesgo de leakage.

## 7. Pendientes para TP2

| # | Pendiente | Archivo a modificar |
|---|---|---|
| 1 | Alinear el notebook para que use los outputs del pipeline completo en lugar de una muestra propia | `TP1_exploracion_mercado.ipynb` |
| 2 | Documentar la limitación de `price_bucket` y comparar resultados con/sin bucket | `reporte_final.md`, notebook |
| 3 | Revisar consistencia entre afirmaciones del texto y números de los outputs | Todo el entregable |
| 4 | Definir si el percentil 99.9 es el corte correcto para outliers | `auxiliary_functions.py` |

---

## 8. Archivos modificados

```text
TP1_corregido/
├── auxiliary_functions.py                    # mapping, expansión, baselines, outliers
├── pipeline_build_baselines.py               # conserva nights y match_level
├── config.py                                 # columnas de baselines actualizadas
├── TP1_exploracion_mercado.ipynb             # días de semana, SNR con soporte
├── README.md                                 # instrucciones actualizadas
├── reporte_final.md                          # síntesis ejecutiva
├── INFORME_CORRECCIONES_TP1.md               # este informe
└── scripts/
    └── destination_mapping_preprocess.py     # referencia del docente
```

---

## 9. Cómo reproducir

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar generación de baselines
python pipeline_build_baselines.py
```

El pipeline generará los outputs en `outputs/`.

Para ejecutar el notebook:

```bash
jupyter notebook TP1_exploracion_mercado.ipynb
```
