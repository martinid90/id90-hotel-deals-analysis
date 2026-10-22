# Reporte crítico de testeo y generalización (TP3)

Fecha: 2026-10-21

## 1) Verificación real de funcionamiento (runtime)

Se volvió a ejecutar el benchmark con ambas APIs levantadas en Docker y endpoints activos:
- Grupo 01: `GET /health` OK
- Grupo 02: `GET /health` OK
- Script comparativo ejecutado: `evaluate_apis.py`
- Archivos regenerados:
  - `api_results_comparativo.csv`
  - `comparativo_metricas.csv`

Resultado operativo: **sí, ambos servicios responden bien** y son reproducibles en el entorno actual.

---

## 2) Qué tan bueno es el set de test actual para generalizar

Set actual: `api_test_cases.csv` con **8 casos**.

### Fortalezas
- Permite prueba de humo end-to-end (API viva, schema, decisión, explicación).
- Cubre dos rutas importantes:
  - casos mapeados de destino,
  - fallback geográfico (`UnknownCity`).
- Incluye algunos escenarios extremos de precio (muy bajo / muy alto).

### Debilidades críticas
1. **Tamaño insuficiente para inferencia estadística**
   - 8 casos no permiten estimar desempeño generalizable.
   - Cualquier métrica tiene varianza alta y puede cambiar mucho con 1 caso.

2. **Etiquetas esperadas no independientes del diseño**
   - Ejemplo explícito: TC001 está marcado como “Ejemplo base enviado por grupo 01”.
   - Hay riesgo de sesgo a favor de la lógica de quien propuso los casos.

3. **Cobertura de escenarios incompleta**
   - No hay casos explícitos de `invalid_input`, `invalid_price`, `insufficient_data`.
   - No hay batería de casos “cerca del umbral” (zona gris), que es donde más se separan los modelos.

4. **Predominio de contextos de alto soporte/hotspots**
   - Varios casos están en destinos muy frecuentes (Orlando, Las Vegas).
   - Esto mide interpolación en mercados conocidos, no extrapolación a mercados de cola.

5. **Posible riesgo de “evaluar parecido al entrenamiento” (sin fuga directa de filas)**
   - El entrenamiento fue 2024 y el test manual usa 2025 (bien temporalmente),
   - pero los contextos de destino/mes sí son, en su mayoría, de mercados ya muy vistos.

---

## 3) Evidencia de solapamiento de contexto con entrenamiento

Cruce manual contra históricos mostró (misma ciudad/estado/país, mes, noches y ocupación):
- TC001 (Orlando): ~58 filas comparables en 2024
- TC002 (Orlando): ~58 filas comparables en 2024
- TC008 (Las Vegas): ~71 filas comparables en 2024
- TC004 (Cancún): ~11 filas comparables en 2024
- Casos como `UnknownCity`: 0 (sirve para fallback)

Conclusión:
- **No parece fuga fila-a-fila**, pero sí hay **fuerte solapamiento de contexto** en varios casos.
- Por eso este set evalúa más “consistencia local en mercados conocidos” que generalización amplia.

---

## 4) Qué está midiendo realmente el benchmark actual

Con 8 casos, hoy se mide principalmente:
1. disponibilidad técnica de API,
2. coherencia de contrato y respuesta,
3. reacción ante precios extremos en pocos destinos,
4. diferencias metodológicas de unidad de precio.

No mide bien:
- robustez fuera de distribución,
- estabilidad por segmento de mercado,
- sensibilidad/especificidad por bandas de descuento con potencia estadística.

---

## 5) Cómo funcionó cada grupo y por qué

Fuente: `comparativo_metricas.csv` y `api_results_comparativo.csv`.

## Grupo 01
- Accuracy: 0.875 (7/8)
- Precision: 1.0
- Recall: 0.667
- F1: 0.8

### Dónde funciona bien
- Detecta ofertas claras en Orlando y Las Vegas (TC001, TC008).
- Mantiene control de falsos positivos en los no-deal del set.

### Dónde falla
- TC004 (Cancún muy barato) lo marca `sospechoso` en vez de `deal`.

### Por qué falla en TC004
- Tiene regla explícita anti-error de carga: si el precio cae por debajo de un factor extremo del típico, prioriza “sospechoso” para no recomendar potenciales errores.
- Es un fallo respecto de la etiqueta del set, pero consistente con su política de seguridad operativa.

## Grupo 02
- Accuracy: 0.625 (5/8)
- Recall: 0.0 para `deal` en este set.

### Dónde funciona bien
- Clasifica consistentemente los `no_deal` del set.
- Respuesta API es estable y explicativa.

### Dónde falla
- No detecta ninguno de los 3 casos etiquetados como `deal`.

### Por qué falla
- Su baseline de referencia para varios contextos es muy bajo en `price_std`.
- Con la normalización usada, muchos precios quedan por encima de la mediana contextual y no cruzan umbral de `deal`.
- Además, hay **riesgo de ambigüedad de unidad de precio** (`price_total` vs `avg_price_average`) documentado por el propio grupo.

---

## 6) Punto metodológico más delicado: unidad de precio

En Grupo 02 la decisión cambia fuerte según cómo se interprete `price_total`:
- Si se manda valor alto (multiplicado por noches/personas), `price_std` sube y casi siempre termina en `no_deal`.
- Incluso sin multiplicar, el caso Orlando=95 no llega a `deal`; para ese contexto responde `deal` recién en valores mucho más bajos (ejemplo observado: alrededor de 30).

Esto no invalida el modelo, pero sí exige:
1. contrato de API inequívoco,
2. ejemplos oficiales consistentes con la unidad,
3. test suite separada por convención de unidad para evitar comparaciones injustas.

---

## 7) ¿Se puede generalizar con lo actual?

**No de manera fuerte.**

Con este set sí se puede afirmar:
- ambas APIs están operativas,
- Grupo 01 detecta mejor las ofertas claras definidas en estos 8 casos,
- Grupo 02 está más conservador para emitir `deal`.

Pero **no** se puede afirmar con solidez:
- desempeño global por país/mercado,
- comportamiento fuera de mercados frecuentes,
- superioridad estadística definitiva entre grupos.

---

## 8) Recomendación para una evaluación realmente generalizable

Pasar de 8 casos a una batería estratificada (mínimo 200–500 casos etiquetados) con:

1. **Partición temporal estricta**
   - train: 2024
   - test ciego: 2025 (sin tocar para diseñar reglas)

2. **Estratos obligatorios**
   - destinos de alto, medio y bajo soporte,
   - mapeados y no mapeados,
   - por región/país,
   - por duración de estadía,
   - por ocupación.

3. **Bandas de descuento**
   - extremos (−60%, −50%),
   - intermedios (−30%, −20%),
   - zona gris cercana a umbral (−15% a −5%),
   - no-ofertas (+0% a +30%).

4. **Casos de robustez API**
   - `invalid_input`, `invalid_price`, `insufficient_data`,
   - payload incompleto,
   - tipos incorrectos.

5. **Métricas por segmento**
   - no solo globales; reportar recall/FPR por estrato.

6. **Contrato común de evaluación**
   - definir una única convención de precio para ambos grupos,
   - o evaluar dos tracks explícitos y no mezclar.

---

## 9) Dictamen técnico actual (honesto y accionable)

- **Funcionamiento**: validado, ambas APIs responden y el benchmark corre.
- **Calidad de evidencia**: útil para smoke test, insuficiente para generalización fuerte.
- **Comparación actual**: favorece a Grupo 01 en detección de `deal` dentro de este set pequeño.
- **Riesgo principal de interpretación**: ambigüedad de unidad de precio (especialmente Grupo 02).
- **Siguiente paso obligatorio**: ampliar set y estandarizar contrato de entrada antes de cerrar una conclusión “definitiva” de performance.
