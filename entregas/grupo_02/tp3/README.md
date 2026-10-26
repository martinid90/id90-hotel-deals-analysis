# Grupo 2 — TP3: Algoritmo de detección de ofertas

**Diplomatura en Ciencia de Datos · Mentoría ID90Travel 2026**
Jeremías Taran, Martín Gabriel Gómez, Jael Mataloni, Francisco Cisneros

## Notebook principal

`grupo_02_tp3.ipynb`. Su gemelo en texto es `grupo_02_tp3.py` (jupytext).

Es una lectura que muestra los resultados del dataset completo y corre rapido porque lee las tablas de `outputs/full/`, sin recalcular. El cálculo está en `src/hotel_deals/`.

**Notebook auxiliar:** `anexo_tp3_pipeline_completo.ipynb` corre el pipeline completo (~30 min) y muestra todas las tablas.

## Objetivo

Implementar y evaluar un mecanismo que clasifique si un precio observado es inusualmente bajo para su contexto
---

## Resultado en una línea

El **detector híbrido con cascada de fallback** ($z_{\log} < -1$ y descuento ≥ 20%, contra la historia 2024 del contexto) decide en el **98,9%** de las búsquedas de 2025 con **F1 = 0,764** (precision 0,725, recall 0,806, FPR 5,4%). Un HistGradientBoosting con features exógenas queda apenas por encima (F1 0,770), pero se elige el híbrido por explicabilidad y operabilidad. El detalle está en [`reporte_final.md`](reporte_final.md).

---

### Qué método elegimos y por qué

**Detector híbrido con cascada de fallback (algoritmo E).**

- **Regla:** `is_deal = (z_log < -1) AND (1 - precio / mediana_contexto >= 0.20)`, con estadísticos calculados sobre la historia del contexto.
- **Contexto:** `destino × mes × semana × estadía`
- **Cascada:** si el contexto no tiene 30 búsquedas independientes, baja a niveles menos específicos: L2 destino×mes×estadía, L3 destino×mes, L4 destino×estadía, L5 destino y L6 país×mes×estadía. Si ninguno alcanza, responde `insufficient_data`.

Lo comparamos contra seis alternativas sobre el test temporal 2025:

| Algoritmo | Precision | Recall | F1 | FPR | Cobertura |
|---|---:|---:|---:|---:|---:|
| A Naive aleatorio | 0,151 | 0,151 | 0,151 | 0,150 | 100% |
| B Naive mediana −20% | 0,375 | 0,965 | 0,540 | 0,285 | 99,8% |
| C Z-score gaussiano (docente) | 0,783 | 0,461 | 0,580 | 0,023 | 99,8% |
| D Percentil 10 | 0,760 | 0,718 | 0,738 | 0,040 | 99,8% |
| **E Híbrido + cascada (elegido)** | **0,725** | **0,806** | **0,764** | **0,054** | **99,8%** |
| F HistGradientBoosting | 0,756 | 0,785 | 0,770 | 0,045 | 100% |
| G Random Forest | 0,713 | 0,743 | 0,728 | 0,053 | 100% |

Por qué E y no F, que tiene un F1 apenas mayor:
- **Explicable.** Cada respuesta trae la mediana de referencia, el descuento, el $z_{\log}$ y el nivel de la cascada.
- **Pocos datos de entrada.** Solo necesita los campos de la búsqueda. El ML usa `avg_hotel_count`, que no viene en la query.
- **Fácil de mantener.** Se actualiza recalculando medianas, sin reentrenar.
- **Mismo comportamiento** frente a descuentos controlados.

### Qué supuestos hace el algoritmo

1. **Precio comparable.** El precio se compara en USD por habitación-noche-persona, igual que en el TP2.
2. **Mercado comparable.** Un mercado comparable es el mismo destino canónico, mes, semana y tramo de estadía. Si no hay masa suficiente, un nivel más agregado es un sustituto razonable.
3. **Soporte mínimo.** 30 **búsquedas independientes** (`n_records`) bastan para estimar mediana y dispersión. No se usa demanda ponderada: las repeticiones (`count_repeated`) no aportan información nueva.
4. **Distribución log-normal.** El precio sigue una distribución aproximadamente log-normal dentro del contexto. Por eso el z se calcula en logaritmo.
5. **Historia representativa.** La historia reciente representa el mercado futuro. Ese supuesto **falla parcialmente**: la deriva entre años es la principal fuente de error.

### Cómo evaluamos sin etiquetas externas

- **Split temporal.** Todo se ajusta con check-ins 2024: baselines, corte de outliers, encoders y modelos. Se evalúa sobre 2025.
- **Etiqueta de referencia.** Es la regla del TP2 aplicada sobre la **distribución realizada del mercado 2025**, que ningún detector ve. La pregunta que se responde es si la historia anticipa qué precios resultan oferta.
- **Control aleatorio.** Un split 80/20 dentro de 2024 da un F1 de 0,919 para E. Eso muestra cuánto infla la evaluación in-period.
- **Casos sintéticos.** Precios fijados en factores de 0,3 a 1,5 de la mediana. La verdad queda definida por construcción.
- **Test set compartido.** Lo evaluamos de punta a punta a través del servicio de la API.
- **Anti-leakage.** `price_bucket` no entra al modelo ni al baseline. El ML no recibe mediana, z ni percentiles.

### Qué sensibilidad tiene el resultado a la definición de mercado y contexto

| Variante | F1 | Precision | Cobertura |
|---|---:|---:|---:|
| Cascada completa (elegida) | 0,764 | 0,725 | 99,8% |
| Solo contexto TP2, sin fallback | 0,812 | 0,764 | **44,6%** |
| Cascada sin semana del mes (*post-hoc*) | **0,775** | **0,745** | 99,8% |
| Cascada sin nivel país | 0,761 | 0,721 | 94,3% |
| Solo destino | 0,644 | 0,641 | 94,3% |
| Soporte con `demand_weight ≥ 30` en vez de `n_records` | 0,736 | 0,691 | 100% |

- **La estacionalidad y la estadía importan.** Usar solo el destino pierde 12 puntos de F1.
- **La semana del mes resta.** Con un año de historia, esa celda es demasiado chica y no generaliza al año siguiente. Lo detectamos mirando el test, así que se recomienda validarlo con datos nuevos antes de adoptarlo.
- **Los umbrales de outliers casi no influyen.** Entre p99 y sin corte, el F1 varía menos de 0,001. El corte p99.9 queda como definitivo.

### Qué limitaciones quedan abiertas

La mediana para búsquedas de 2 adultos y 1 habitación casi no crece con la cantidad de noches (muestra 300k):

| Noches | 1 | 2 | 3 | 5 | 7 |
|---|---:|---:|---:|---:|---:|
| Mediana de `avg_price_average` (USD) | 138 | 153 | 177 | 193 | 208 |

Si el precio fuera el total, debería crecer de forma proporcional. La fórmula de `price_std` que decidimos usar `precio / (noches × habitaciones × personas)`, divide igual por las noches. En ese caso, cuanto más larga la estadía, más barato parece el precio:

- **Señal en los resultados.** La tasa de ofertas es del 26,3% en estadías largas (más de 5 noches), contra 12,5% en cortas y 14,2% en medias.
- **Por qué no se corrigió.** Mantuvimos la fórmula por consistencia con la definición acordada.
- **Corrección propuesta.** `price_std = precio / (habitaciones × personas)`

**Otras limitaciones:**

1. **No hay categoría de hotel.** El mercado mezcla hoteles económicos y de lujo, y eso infla la dispersión.
2. **Hay deriva temporal** Los baselines deberían recalcularse con ventana móvil, tener datos de mas años Tambien podria solucionar parte del problema.
3. **La API sirve baselines de 2024**, para que el test set sea reevaluable sin fuga.

## Conclusión

Definimos una regla (z logarítmico más descuento mínimo), sobre un contexto con cascada de fallback, detecta ofertas en el año siguiente con F1 0,76 y cobertura del 99%. Rinde igual que un modelo de boosting y es explicable y simple de operar. El cuello de botella ya no es el algoritmo sino **la definición de mercado**:
- falta categoría de hotel;
- los precios derivan entre años.

---

## Cómo reproducir

Requiere Python 3.10 o superior. Todos los comandos se corren desde esta carpeta.

```bash
pip install -r requirements.txt

# A) Muestra incluida (300k búsquedas, ~1,5 min)
python scripts/run_pipeline.py

# B) Dataset completo (~5,1 M búsquedas, ~30 min, ~5 GB RAM). Números oficiales del informe.
#    Los CSV datos_historicos_*.csv van en data/ o en la carpeta indicada por HOTEL_DATA_DIR.
HOTEL_DATA_DIR=/ruta/a/los/csv python scripts/run_pipeline.py --source full
#    PowerShell:  $env:HOTEL_DATA_DIR="..\TP2_entrega\data"; python scripts/run_pipeline.py --source full

# Notebook principal (lee outputs/full, o outputs/sample si no existe; corre en segundos)
python -m jupytext --to ipynb grupo_02_tp3.py   # solo si se editó el .py
python -m nbconvert --to notebook --execute --inplace grupo_02_tp3.ipynb

# Anexo: corre el pipeline completo (usa "full" si encuentra los CSV; forzar muestra con TP3_SOURCE=sample)
python -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=7200 anexo_tp3_pipeline_completo.ipynb

# Tests (cascada, métricas, API, casos borde)
python -m pytest -q tests
```

Cada corrida escribe:

| Ruta | Contenido |
|---|---|
| `outputs/<sample\|full>/` | Todas las tablas del informe: métricas, errores, sensibilidad, sintéticos, casos borde |
| `outputs/<sample\|full>/figuras/` | Gráficos PNG del informe (también con `python -m hotel_deals.figures full`, con `src` en el `PYTHONPATH`) |
| `artifacts/<sample\|full>/` | Baselines por nivel de cascada y `params.json` (lo que sirve la API) |
| `data/test_set/test_set_<fuente>.csv` | Test set compartido en formato de query |

## API y Docker

```bash
docker build -t hotel-deals-g2 .
docker run -p 8000:8000 hotel-deals-g2
# Documentación interactiva: http://localhost:8000/docs
```

Sin Docker: `uvicorn api.main:app --port 8000`. La API sirve `artifacts/full` si existe y, si no, `artifacts/sample`. Se puede forzar con `HOTEL_ARTIFACTS_DIR`.

### Formato de query

`POST /evaluate` (o `POST /evaluate/batch` con una lista):

```json
{
  "city": "Orlando",
  "state": "Florida",
  "country": "United States",
  "country_code": "US",
  "date_start": "2025-07-10",
  "nights": 3,
  "adults": 2,
  "kids": 0,
  "rooms": 1,
  "price_total": 30.0
}
```

| Campo | Obligatorio | Descripción |
|---|---|---|
| `country_code` | sí | ISO-3166 alfa-2 |
| `date_start` | sí | Check-in, formato `YYYY-MM-DD` |
| `nights`, `adults` | sí | |
| `price_total` | sí | USD de la estadía, en la misma unidad que `avg_price_average` del dataset (ver *Riesgo principal*) |
| `city`, `state`, `country` | no | Mejoran el mapping |
| `kids` | no | Por defecto 0 |
| `rooms` | no | Por defecto 1 |

### Respuesta

Esta es la respuesta real que devuelve la API con los artefactos del dataset completo:

```json
{
  "decision": "deal",
  "is_deal": true,
  "price_std": 5.0,
  "baseline_median": 14.7989,
  "discount": 0.6621,
  "z_log": -1.3488,
  "baseline_level": "L1_dest_mes_semana_estadia",
  "baseline_n_records": 171.0,
  "destination_final": "663",
  "destination_name": "Orlando",
  "is_mapped": true,
  "explanation": "Oferta: 5.00 USD por habitación-noche-persona está 66% debajo de la mediana de destino × mes × semana × estadía (14.80 USD, 171 búsquedas) y su z_log es -1.35 (umbral -1)."
}
```

Con `price_total` igual a 40, el descuento es de 55% pero $z_{\log} = -0{,}99$, así que la decisión es `no_deal`. Con 150, también es `no_deal`. El campo `explanation` da el motivo en texto en todos los casos, incluidos `insufficient_data` e `invalid_price`.

`decision` puede tomar estos valores:

| Valor | Significado |
|---|---|
| `deal` / `no_deal` | El sistema decidió |
| `insufficient_data` | No hay soporte en ningún nivel de la cascada |
| `invalid_price` | Menos de 1 USD por habitación-noche-persona |
| `invalid_input` | Noches fuera de 1–30, 0 habitaciones o 0 personas |

## Estructura

```text
TP3_entrega/
├── README.md                  este archivo
├── reporte_final.md           síntesis ejecutiva
├── grupo_02_tp3.ipynb / .py   notebook principal (ejecutado) + gemelo jupytext
├── anexo_tp3_pipeline_completo.ipynb / .py   auxiliar: pipeline completo y tablas de detalle
├── src/hotel_deals/
│   ├── config.py              todas las decisiones fijas (umbrales, cascada, soporte)
│   ├── data.py                carga, curación, outliers (WinsorCap ajustado en train)
│   ├── geo.py                 mapping a destinos canónicos + fallback de ciudad
│   ├── baselines.py           cascada de baselines por contexto
│   ├── detectors.py           detectores A–E y etiqueta de referencia
│   ├── ml.py                  HistGradientBoosting / RandomForest (features exógenas)
│   ├── evaluation.py          métricas (incluye cobertura y FPR)
│   ├── test_set.py            construcción del test set compartido
│   ├── service.py             DealDetector: lo que usa la API (decisión + explicación)
│   ├── figures.py             gráficos del informe a partir de outputs/
│   └── pipeline.py            flujo completo
├── api/main.py                FastAPI
├── scripts/run_pipeline.py    CLI del pipeline
├── tests/test_system.py       pytest
├── data/                      mapping, muestra 300k, test_set/
├── artifacts/                 baselines servidos por la API
├── outputs/                   tablas generadas
├── Dockerfile, requirements-api.txt (imagen) y requirements.txt (desarrollo)
```
