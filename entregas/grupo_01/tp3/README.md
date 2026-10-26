# TP3 — Detector de ofertas hoteleras con evaluación reproducible

Grupo 1 · Diplodatos 2026

**Integrantes:** Camila Ines Amado, Francisco Risculese, Agustin Macrina y Lucila Pasquetta

**Pregunta:** dado un precio de hotel en un contexto (lugar, fecha, ocupación), ¿es inusualmente bajo para su mercado?

**Respuesta corta:** se eligió un detector robusto (mediana y MAD del log-precio por destino × mes, con descuento mínimo del 20%,
filtro de errores de carga y fallback jerárquico hasta país). En un test separado con casos controlados logra **precisión 0,996,
recall 0,76, F1 0,86 y 0,3% de falsos positivos**, con 99,8% de cobertura, y de los cuatro modelos comparados es el único que no
recomienda errores de carga como ofertas. Se expone con una API FastAPI dentro de un contenedor Docker.

El resumen ejecutivo está en [`reporte_final.md`](reporte_final.md) y el detalle en [`TP3- Grupo 1_VersionFinal.ipynb`](TP3-%20Grupo%201_VersionFinal.ipynb).

---

## 1. Estructura

```
entregas/grupo_01/tp3_pupi_v2/
├── README.md                     ← este archivo
├── reporte_final.md              ← síntesis ejecutiva
├── TP3- Grupo 1_VersionFinal.ipynb ← notebook principal (muestra e interpreta resultados)
├── pyproject.toml                ← paquete instalable (pip install -e .)
├── requirements.txt              ← entorno completo (pipeline, notebook, tests)
├── requirements-api.txt          ← solo lo que usa la API en Docker
├── Dockerfile / .dockerignore
├── src/ofertas_hoteles/
│   ├── config.py                 ← TODOS los parámetros y rutas
│   ├── mapping.py                ← geografía cruda → destino canónico (lógica de referencia del repo)
│   ├── data.py                   ← muestreo por chunks, filtros de validez (sin eliminar datos), features
│   ├── references.py             ← tablas de referencia por contexto + fallback + price_bucket
│   ├── testset.py                ← diseño de los sets de validación y test
│   ├── models.py                 ← los 4 algoritmos principales y las variantes del anexo
│   ├── evaluate.py               ← métricas, IC por bootstrap, elección de umbral, análisis de errores
│   ├── report.py                 ← figuras
│   ├── estadistica.py            ← homogeneidad 2024 vs 2025 por mes
│   ├── diagnostics.py            ← cobertura del mapeo y representatividad de la muestra (dataset completo)
│   ├── pipeline.py               ← corrida de punta a punta
│   ├── scorer.py                 ← scorer liviano de producción (sin sklearn)
│   └── api.py                    ← API FastAPI
├── data/
│   ├── destination_with_nearest.csv   ← tabla de mapeo (la usa la API)
│   ├── val_set.csv.gz                 ← set de validación (compartible)
│   └── test_set.csv.gz                ← set de TEST (compartible)
├── models/                       ← modelo final exportado (tablas de referencia + modelo_meta.json)
├── outputs/                      ← métricas, grillas, análisis de errores, figuras, predicciones
├── examples/                     ← formato de query para la API (simple y batch)
├── scripts/
│   ├── probar_api.py             ← manda las queries de ejemplo a la API
│   ├── sensibilidad_unidad_precio.py ← repite todo con la fórmula alternativa de precio (sección 6)
│   └── sensibilidad_noches.py    ← contexto separado por cantidad de noches (sección 6.1)
└── tests/                        ← tests de API, consistencia y fugas
```

## 2. Datos

| Archivo | Dónde va | ¿Se sube? |
|---|---|---|
| `datos_historicos_2024.csv`, `datos_historicos_2025.csv` | `data/` en la **raíz del repo** (como siempre) | No (≈570 MB) |
| `destination_with_nearest.csv` | copia en `tp3_pupi_v2/data/` | Sí (1,2 MB) |
| `val_set.csv.gz`, `test_set.csv.gz` | `tp3_pupi_v2/data/` | Sí (≈6 MB) |
| `data/interim/muestra_*.parquet` | se generan solos | No |

Si los CSV crudos están en otro lado: variable de entorno `TP3_RAW_DIR`.

## 3. Cómo correrlo

Requisitos: Python 3.12 (probado también con 3.13). Pico de RAM ≈ 1,1 GB.

**Windows (PowerShell)**, parada en `entregas\grupo_01\tp3_pupi_v2`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .

python -m ofertas_hoteles.pipeline     # todo de cero (~2 min): muestras → sets → modelos → métricas → modelo final → diagnósticos
python scripts/sensibilidad_unidad_precio.py   # opcional: sección 6
python scripts/sensibilidad_noches.py          # opcional: sección 6.1
pytest                                 # 10 tests: API, consistencia API = modelo evaluado, sin fugas
jupyter nbconvert --execute --to notebook --inplace "TP3- Grupo 1_VersionFinal.ipynb"
```

**Linux / Mac:** igual, activando con `source .venv/bin/activate`.

Pasos sueltos: `python -m ofertas_hoteles.pipeline --desde 3` (reusa muestras y sets) o `--hasta 2`.
Si la compu se queda sin memoria: `$env:TP3_FRAC_TRAIN="0.10"` antes de correr (los números cambian un poco).

Los `.csv.gz` se guardan sin marca de tiempo: si el contenido no cambia, git no los marca como modificados.

La corrida es determinística (semilla 42): se verificó con Python 3.12 en un entorno limpio (`requirements.txt`) que correr todo
desde cero reproduce exactamente los mismos datos, métricas y modelo entregados.

## 4. API y Docker

```bash
docker build -t ofertas-hoteles:tp3 .
docker run --rm -p 8000:8000 ofertas-hoteles:tp3
# documentación interactiva: http://localhost:8000/docs
python scripts/probar_api.py
```

Sin Docker: `uvicorn ofertas_hoteles.api:app --port 8000`.

### Formato de la query (`POST /predict`)

```json
{
  "city": "Orlando",
  "state": "Florida",
  "country": "United States of America",
  "country_code": "us",
  "date_start": "2025-07-10",
  "date_end": "2025-07-13",
  "adults": 2,
  "kids": 0,
  "rooms": 1,
  "price": 95.0
}
```

| Campo | Obligatorio | Descripción |
|---|---|---|
| `city` | sí | ciudad tal como viene en la búsqueda |
| `country_code` | sí | código ISO del país (`us`, `ar`, `mx`…) |
| `date_start` | sí | check-in `YYYY-MM-DD` (define el mes del contexto) |
| `price` | sí | **precio promedio por habitación y por noche en USD** (igual que `avg_price_average`) |
| `state`, `country` | no | mejoran el mapeo a destino canónico |
| `date_end` o `nights` | no | si van los dos tienen que coincidir; por defecto 1 noche |
| `adults`, `kids`, `rooms` | no | por defecto 2, 0, 1 |

### Respuesta

```json
{
  "oferta": "SI",
  "decision": "oferta",
  "is_deal": true,
  "mensaje": "Precio 41% por debajo del típico de su mercado.",
  "precio_comparable": 95.0,
  "noches": 3,
  "precio_referencia": 160.75,
  "descuento": 0.409,
  "z_robusto": -1.515,
  "nivel_contexto": "destino_mes",
  "confianza": "alta",
  "n_referencia": 326,
  "demanda_referencia": 3547,
  "destino": {"id": "663", "nombre": "Orlando", "mapeado": true, "match_level": "cc_state_code_city", "pais": "US"}
}
```

**`oferta` es la respuesta final: `"SI"` o `"NO"`.** El resto de los campos explica el porqué. `precio_comparable` es el
precio por habitación-noche tal como llega (no se divide); `noches` se devuelve para trazar el contexto. `n_referencia` y
`demanda_referencia` dicen cuántas búsquedas de 2024 (y cuánta demanda, suma de `count_repeated`) sostienen la referencia.
`decision` ∈ `oferta` · `normal` · `sospechoso` (precio < 20% del típico: probable error de carga) · `sin_soporte` (no hay
historial: el sistema no decide). Solo `decision = oferta` da `oferta: "SI"`; `normal`, `sospechoso` y `sin_soporte` dan `"NO"`. Otros endpoints: `POST /predict/batch` (hasta 1000 queries), `GET /health`, `GET /model`.

**Fallback:** destino × mes → destino → país × mes → país → `sin_soporte`, siempre con ≥ 30 búsquedas de 2024.
Ciudad que no mapea → se usa la clave cruda país|estado|ciudad y, si no tiene historial, cae a país. País desconocido →
`sin_soporte` con HTTP 200. Entradas inválidas (precio ≤ 0, check-out antes del check-in, noches que no coinciden) → HTTP 422.

## 5. Qué cambia respecto del TP2

El TP3 continúa el TP2 (misma pregunta, destino canónico, escenarios A/B, soporte mínimo 30, sin borrar outliers; el experimento de "caída de 20%" pasó a ser el test controlado), pero revisa cinco decisiones con evidencia:

| Tema | TP2 | TP3 | Por qué |
|---|---|---|---|
| Escenario de mercado | B: destino × mes × `price_bucket` | **A: destino × mes** (B se sigue evaluando) | La ventaja de B (menos dispersión, 69,9% de "Deal" ante −20% vs 45,6% en A) tiene una limitación conocida: el bucket sale del mismo precio evaluado, así que una rebaja puede cambiar de gama. Comparando directamente con y sin bucket en el mismo test, B detecta menos (recall 0,73 vs 0,76). |
| Unidad de análisis | noche pagada | **búsqueda**, contexto = mes de check-in | La decisión es por consulta; expandir repetía el precio e inflaba el soporte. Solo 5,8% de las estadías cruza de mes. |
| Precio comparable | precio / (noches × habitaciones × personas) | **`avg_price_average`** (habitación-noche) | Elasticidad del precio a noches ≈ 0,05 y a habitaciones ≈ 0,02: ya viene normalizado. Dividir por noches × habitaciones × personas en todas las filas deja casi ciegos a los modelos (F1 del propuesto 0,28). Además, el código del repo (`standardize_prices`), por un error, solo dividía el 5% de las filas: mezclaba dos unidades. |
| Mapeo de destinos | función del repo: 28–36% de match | **lógica de referencia del repo**: 69% filas / 81% demanda | Corrige mayúsculas, claves de 2 partes, alias de EE.UU.; deja `match_level`. |
| `count_repeated` | peso de demanda en baselines | referencias sin ponderar + **métricas ponderadas por demanda** como chequeo | Soporte = cantidad de búsquedas (todas se conservan); ponderado, el propuesto da F1 0,89 y el ranking no cambia. |

## 5b. Supuestos y decisiones metodológicas

1. **Unidad de análisis = búsqueda** (fila original), contexto temporal = mes de check-in. No se expande a noches: la decisión es
   por consulta y la expansión repetía el mismo precio (inflaba el soporte). Solo 5,8% de las estadías cruza de mes.
2. **Precio comparable = `avg_price_average`** (por habitación-noche). Dentro de destino × mes la elasticidad del precio a noches es
   ≈ 0,05 y a habitaciones ≈ 0,02: ya viene normalizado. La fórmula /(noches × habitaciones × personas) se evaluó como
   sensibilidad y triplica la dispersión (ver `outputs/sensibilidad_unidad_precio/`). 
   **Una sola unidad:** se usa `avg_price_average` sin dividir, como única unidad en todo el pipeline (referencias,
   test y API); nunca se normaliza dos veces. **Duración de la estadía:** se guarda `nights` en cada registro y se probó el
   contexto destino × mes × grupo de noches (1 / 2–3 / 4–6 / 7+) con `scripts/sensibilidad_noches.py`. Dentro de cada
   destino × mes el precio por noche varía menos de 1,1% entre grupos y el F1 queda igual (0,862 vs 0,861, intervalos
   superpuestos), así que se mantiene destino × mes, que tiene más soporte (ver `outputs/sensibilidad_noches/`).
3. **Mapeo de destinos** con la lógica de referencia del repo (`scripts/destination_mapping_preprocess.py`). Sobre el histórico completo 2024 + 2025
   (`outputs/diagnosticos/`): **69,0% de las filas, 80,5% de la demanda y 35,6% de las geografías únicas** mapeadas
   (idéntico a la corrida de referencia). Se reportan además las filas por `match_level` y el top de no mapeados por demanda.
   Lo no mapeado no se descarta: queda con clave cruda país|estado|ciudad y cae al fallback por país si no tiene historial.
   **Representatividad de la muestra:** la muestra del 20% difiere del total en menos de 0,1 puntos porcentuales por mes,
   país (top 15) y destino (top 20), y en menos de 1% en los cuantiles de precio.
4. **Separación temporal:** los modelos solo ven 2024. `price_bucket` se corta con 2024 y se asigna sobre el precio que se evalúa.
5. **Soporte mínimo:** 30 búsquedas por contexto.
6. **No se elimina ningún dato:** los filtros de validez no descartan filas en ninguno de los dos años; las búsquedas repetidas
   (0,03%) y los precios extremos se conservan. Los extremos se manejan con mediana/MAD (que no se dejan
   arrastrar por ellos) y la regla de "sospechoso".
7. **Lo que fue normal en 2024 sigue siendo normal en 2025** (las referencias no se actualizan).
8. **Una rebaja artificial del precio se parece a una oferta real** (base de los casos controlados).

## 6. Diseño del set de test

Ver sección 2 del notebook y `src/ofertas_hoteles/testset.py`. Resumen:

- 2025 se divide en tres pools disjuntos por grupo destino × fecha de check-in: **mercado** (40%, solo para construir la "verdad"),
  **val** (30%, para elegir umbrales) y **test** (30%, se usa al final).
- **3.000 anclas** (búsquedas reales con precio a ±10% de la mediana de mercado 2025 de su contexto), estratificadas por volumen del
  destino, trimestre y nivel de precio del mercado. A cada una: −60/−50/−40/−30% (oferta clara), −20/−10% (gris, sin etiqueta),
  0/+10/+20/+30/+50% (no oferta), −90% (error de carga).
- **20.000 búsquedas reales** sin tocar, para cobertura y tasa de alertas.
- Chequeos automáticos (`tests/test_consistencia.py`): ningún `search_id` ni grupo destino×fecha compartido entre val y test,
  test 100% 2025, etiquetas coherentes con el diseño.

## 7. Métricas

Precisión, recall, F1, tasa de falsos positivos y cobertura, más dos operativas: tasa de alerta en precios reales y errores de
carga marcados como oferta. Accuracy se reporta pero no se usa para decidir (depende de la proporción de positivos del diseño).
IC 95% por bootstrap de anclas. Justificación completa en el notebook (sección 4).

## 8. Resultados (test)

| Algoritmo | Umbral | Accuracy | Precisión | Recall | F1 [IC 95%] | FPR | Alertas en reales | Errores de carga → oferta |
|---|---|---|---|---|---|---|---|---|
| **Propuesto (A)** | z < −1,5 | 0,891 | 0,996 | 0,758 | **0,861** [0,853–0,867] | 0,3% | 7,6% | **0,4%** |
| Regla de mediana | ≤ 60% de la mediana | 0,850 | 0,989 | 0,670 | 0,798 [0,793–0,804] | 0,6% | 8,7% | 100% |
| Isolation Forest | top 20% anómalo | 0,710 | 0,892 | 0,395 | 0,548 [0,532–0,562] | 3,8% | 10,2% | 65,8% |
| Aleatorio | p = 0,10 | 0,544 | 0,444 | 0,102 | 0,166 [0,152–0,181] | 10,2% | 9,7% | 10,2% |

Cobertura: 100% de los casos etiquetados en los cuatro; 99,8% de las búsquedas reales (100% en el aleatorio, que no usa contexto).

### Anexo: otros modelos que se probaron

Variantes del propuesto con una pieza cambiada (análisis de ablación). Mismo test y mismo criterio de umbral; no compiten por la elección.

| Variante | Qué cambia | F1 | Recall | FPR | Errores de carga → oferta | Qué muestra |
|---|---|---|---|---|---|---|
| MAD puro | sin descuento mínimo ni filtro de errores | 0,863 | 0,762 | 0,4% | 100% | el núcleo detecta igual; las reglas evitan recomendar errores |
| Con `price_bucket` (B) | gama de precio en el contexto | 0,844 | 0,733 | 0,3% | 1,6% | detecta menos: el bucket depende del precio evaluado (limitación declarada) |
| v1 (piso absoluto) | "sospechoso" todo precio < p1 global | 0,809 | 0,681 | 0,3% | 0,4% | castiga mercados baratos |
| z-score del grupo | media/desvío, contexto semana × bucket | 0,839 | 0,731 | 0,9% | 94,7% | más falsos positivos, recomienda errores de carga y deja 14% sin decidir: por qué usar estadística robusta |

**Chequeo ponderado por demanda** (`count_repeated`, `outputs/metricas_test_ponderadas.csv`): el ranking no cambia. El propuesto sube a F1 0,892 (recall 0,806) y marca 4,5% de las búsquedas reales; regla de mediana 0,812; Isolation Forest baja a 0,452.

## 9. Conclusiones

- **Se elige el propuesto (A).** Es el de mejor F1 de la comparación, detecta más que la regla de mediana con FPR de 0,3%, y de los
  cuatro es el único que separa los errores de carga. Las variantes del anexo confirman cada pieza del diseño. Es interpretable y liviano (la API no necesita sklearn ni los datos crudos).
- **Política: precisión antes que recall.** Con `z_cut = −1,5` casi nunca marca como oferta un precio normal (0,3% de falsos
  positivos), a costa de no ver rebajas chicas (49% de las de −30%; descuento mínimo confiable ≈ 33%). Con `z_cut = −1,0`
  detectaría 88% pero marcaría 16% de los precios reales. Se eligió así para no perder la confianza del usuario.
- **Noviembre y diciembre de 2024** tienen muchas menos búsquedas que 2025; el precio a igual destino no cambia, pero en esos
  meses las referencias se apoyan en menos destinos (`outputs/estadistica/homogeneidad_por_mes.csv`).
- **Isolation Forest no conviene acá:** marca combinaciones raras (8+ noches, ocupaciones poco comunes) aunque el precio sea
  normal. El precio relativo al mercado es la señal; el resto de las variables mete ruido.
- **Anexo:** `price_bucket` sigue sin ayudar (recall −2,5 puntos: el bucket depende del precio evaluado); sin las reglas de negocio (MAD puro) se detecta igual pero se recomiendan errores de carga.
- **Fortalezas:** rebajas de 40% o más (72–95% de detección), mercados baratos y medios, destinos con historial.
- **Debilidades:** rebajas de 30% (49%), mercados caros (≈ 56–63%), fallback a país (recall 0,62, FPR 2,8%), destinos nuevos.

## 10. Limitaciones

- Sin etiquetas reales: se mide si detecta rebajas artificiales, no ofertas reales.
- Sin categoría/estrellas del hotel: en mercados caros una rebaja se pierde en la mezcla de gamas.
- El contexto no controla ocupación (elasticidad 0,32: el precio sube ≈ 25% al duplicar personas).
- Una sola partición temporal (2024 → 2025) y referencias estáticas.
- El cambio de la v1 (piso absoluto) a la versión final se detectó mirando errores en test; se decidió con validación y se reportan ambas versiones.
- Muestra de 20% de 2024 y 20% de 2025 por RAM; con más datos mejoraría el soporte de destinos chicos.
- El Dockerfile se verificó instalando exactamente las mismas dependencias y archivos en un entorno limpio; conviene correr
  `docker build` una vez en la máquina de entrega.
