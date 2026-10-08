# Revisión ejecutiva TP2 y habilitación de TP3

Fecha: 2026-10-07

## Resumen corto

- **Grupo 1:** puede pasar a TP3, pero **con condiciones**.
- **Grupo 2:** puede pasar a TP3, también **con condiciones**.

El foco ahora no es volver a TP1, sino evitar errores que después rompan el TP3.

---

## Grupo 1 — comentarios claros para devolución

### Estado
**Listo con condiciones.**

### Qué está bien
- Tienen notebook de TP2 y decisión de contexto para TP3.
- Declaran noche pagada (checkout excluido).
- Comparan escenarios y justifican elección.

Evidencia:
- [entregas/grupo_01/tp2/Hoteles - Grupo 1 - Práctico 2.ipynb](entregas/grupo_01/tp2/Hoteles%20-%20Grupo%201%20-%20Práctico%202.ipynb#L14)
- [entregas/grupo_01/tp2/Hoteles - Grupo 1 - Práctico 2.ipynb](entregas/grupo_01/tp2/Hoteles%20-%20Grupo%201%20-%20Práctico%202.ipynb#L311)
- [entregas/grupo_01/tp2/Hoteles - Grupo 1 - Práctico 2.ipynb](entregas/grupo_01/tp2/Hoteles%20-%20Grupo%201%20-%20Práctico%202.ipynb#L411-L413)

### Comentario único de reproducibilidad/estructura (juntar todo acá)
La estructura de entrega está incompleta para revisión docente rápida (README plantilla y sin cierre final).  
**Pedir PR** con formato completo de entrega: README final, nombre correcto del notebook principal, conclusión cerrada y pasos de ejecución.

Evidencia:
- [entregas/grupo_01/tp2/README.md](entregas/grupo_01/tp2/README.md#L5)
- [entregas/grupo_01/tp2/README.md](entregas/grupo_01/tp2/README.md#L22)

### Riesgos reales para TP3 (error -> por qué importa)
1. **Criterio de confianza no totalmente claro (`count_obs` vs registros independientes).**  
  Usar `>= 30` **no está mal**. El punto es dejar bien definido **30 de qué** (si son registros independientes o demanda ponderada) y mantener esa regla igual en todo TP3.

  En simple: no discutimos el número 30, discutimos que la definición quede fija y auditada.

  **Chequeo de código actual:** en su pipeline, `count_obs` se calcula como suma de `count_repeated` (demanda ponderada), no como cantidad de registros independientes.

  Evidencia:
  - [entregas/grupo_01/tp2/Hoteles - Grupo 1 - Práctico 2.ipynb](entregas/grupo_01/tp2/Hoteles%20-%20Grupo%201%20-%20Práctico%202.ipynb#L333)
  - [entregas/grupo_01/tp2/Hoteles - Grupo 1 - Práctico 2.ipynb](entregas/grupo_01/tp2/Hoteles%20-%20Grupo%201%20-%20Práctico%202.ipynb#L163-L206)
  - [auxiliary_functions.py](auxiliary_functions.py#L700-L708)

2. **Mapping: no es “error”, pero sí limitación del problema.**  
  No alcanza con mapear: en TP3 tienen que dejar explícito fallback geográfico para no perder cobertura.

  En simple: si una ciudad no matchea al destino canónico, definir una regla de respaldo (por ejemplo ciudad cruda o nivel superior) para que el algoritmo no se quede sin respuesta.

  Evidencia:
  - [entregas/grupo_01/tp2/Hoteles - Grupo 1 - Práctico 2.ipynb](entregas/grupo_01/tp2/Hoteles%20-%20Grupo%201%20-%20Práctico%202.ipynb#L519)

3. **Escenario elegido requiere fallback robusto de bucket/contexto.**  
  Si no lo cierran, suben falsos positivos o quedan muchos casos sin decisión.

  Evidencia:
  - [entregas/grupo_01/tp2/Hoteles - Grupo 1 - Práctico 2.ipynb](entregas/grupo_01/tp2/Hoteles%20-%20Grupo%201%20-%20Práctico%202.ipynb#L389)
  - [entregas/grupo_01/tp2/Hoteles - Grupo 1 - Práctico 2.ipynb](entregas/grupo_01/tp2/Hoteles%20-%20Grupo%201%20-%20Práctico%202.ipynb#L413)

---

## Grupo 2 — comentarios claros para devolución

### Estado
**Listo con condiciones.**

### Qué está bien
- Corrigieron puntos fuertes de TP1 (checkout, day-of-week, unidad de análisis).

Evidencia:
- [entregas/grupo_02/tp2/INFORME_CORRECCIONES_TP1.md](entregas/grupo_02/tp2/INFORME_CORRECCIONES_TP1.md#L21)
- [entregas/grupo_02/tp2/INFORME_CORRECCIONES_TP1.md](entregas/grupo_02/tp2/INFORME_CORRECCIONES_TP1.md#L59)
- [entregas/grupo_02/tp2/INFORME_CORRECCIONES_TP1.md](entregas/grupo_02/tp2/INFORME_CORRECCIONES_TP1.md#L75)

### Riesgos reales para TP3 (error -> por qué importa)
1. **Riesgo de circularidad con `price_bucket`.**  
  Estado real hoy: en TP2 **no se ve entrenamiento final de modelo**, pero en el plan de TP3 proponen usar `price_bucket` como feature y la etiqueta `is_deal` se construye desde precio.

  Con esa combinación, el riesgo de leakage es real en TP3 si no separan bien qué variables entran al modelo.

  Comentario práctico para el grupo: evitar darle al modelo una señal que ya contiene información directa del precio usado para etiquetar `is_deal`.

  Evidencia:
  - [entregas/grupo_02/tp2/reporte_final.md](entregas/grupo_02/tp2/reporte_final.md#L100)
  - [entregas/grupo_02/tp2/TP2_curacion_mercado.py](entregas/grupo_02/tp2/TP2_curacion_mercado.py#L601)

2. **Pendientes de consistencia (texto vs output; muestra vs pipeline).**  
  Si no lo cierran, TP3 no queda auditable.

  Pendientes concretos que ellos mismos dejaron:
  - alinear notebook con outputs del pipeline completo,
  - revisar consistencia entre afirmaciones del texto y números reportados,
  - terminar de cerrar comparación con/sin bucket en la documentación.

  Evidencia:
  - [entregas/grupo_02/tp2/INFORME_CORRECCIONES_TP1.md](entregas/grupo_02/tp2/INFORME_CORRECCIONES_TP1.md#L271)

3. **Política de outliers no cerrada (`p99.9`).**  
  Ellos aplican un corte, pero dejaron pendiente validar si ese valor es el correcto para el caso de negocio.

  En simple: no es que “no tienen política”, sino que falta cerrar si ese umbral queda definitivo. Si cambia, cambian baseline, etiqueta y métricas.

  Evidencia:
  - [entregas/grupo_02/tp2/INFORME_CORRECCIONES_TP1.md](entregas/grupo_02/tp2/INFORME_CORRECCIONES_TP1.md#L274)

---

## Qué debe pedir TP3 (explicado simple)

Objetivo del TP3: **diseñar y validar el algoritmo de detección de deals**.

Mínimo que tienen que entregar:
1. Regla/criterio de etiquetado `is_deal` bien definido.
2. Baseline por contexto y fallback cuando no hay soporte.
3. Evaluación con métricas claras.

### Métricas sugeridas (obligar set mínimo)
- `Accuracy` (como referencia general).
- `Precision`, `Recall`, `F1` (centrales para deals).
- Cobertura operativa (% casos donde el sistema decide).
- Tasa de falsos positivos.

Recomendación: además de partición aleatoria, hacer validación temporal (entrenar en período anterior y testear en período posterior).

---

## Comentario final para ambos grupos

Hacer un **PR de cierre de TP2** con información completa (documentación, decisiones cerradas, riesgos y ejecución).  
No es burocracia: esto evita errores de interpretación y facilita revisar TP3 con criterio único.

---

## Mensaje final sugerido para ambos grupos (TP3)

Hola chicos, buenas noches. Ahí terminamos la consulta con los chicos del grupo 1.  
Les dejo un resumen general para que les quede como lineamiento para el práctico 3.  
Para esta entrega, necesitamos un proceso de evaluación serio, trazable y reproducible.

### 1) Formato de entrega
- Estructura de proyecto Python correcta (también les facilita generar el Docker container).
- Referencia de formato: [entregas/devoluciones_tp1.md](entregas/devoluciones_tp1.md)
- Documentación completa (`README`, instrucciones de ejecución, supuestos, métricas, conclusiones).
- Reproducibilidad de punta a punta.
- Reporte final con resumen.
- Set de datos de testeo + explicación de cómo lo diseñaron.
- Docker container para buildear con API embebida para responder.
- Formato de query de input a compartir (por ejemplo: lugar, fecha y campos básicos para responder).

### 2) Dataset de test bien definido
- Armar un set de test separado, sin mezclar con entrenamiento (y compartirlo).
- Evitar repeticiones y fugas de información (revisar especialmente cuándo calculan `price_bucket`).
- Incluir una gama amplia y estratificada de casos (distintos destinos, contextos y precios).
- Agregar casos controlados con precios modificados (por ejemplo, -30% para ofertas claras y también casos caros).
- Incluir variaciones amplias para detectar fortalezas y debilidades del algoritmo.
- Cuidar consistencia de contexto (incluido `price_bucket`) para no introducir errores artificiales.

### 3) Comparación de algoritmos
Comparar al menos:
- Baseline naive aleatorio.
- Baseline naive por mediana/regla simple.
- Algoritmo propuesto por el grupo.
- Algoritmos adicionales que quieran probar.

### 4) Subset de métricas para evaluar y hacer seguimiento
Seleccionar un subconjunto (o todas) y justificar por qué esa combinación:
- `Accuracy`
- `Precision`
- `Recall`
- `F1`
- Cobertura (% de casos donde el sistema puede decidir)
- Tasa de falsos positivos

### 5) Análisis y decisión final
- Comparar métricas entre algoritmos.
- Analizar errores (dónde falla y en qué tipo de casos).
- Elegir un algoritmo final y justificar por qué es mejor para el problema.

### 6) Cuidado metodológico crítico
- Evitar circularidad/leakage: no darle al modelo señales que anticipen directamente la etiqueta.
- Definir fallback robusto para casos sin soporte o sin mapeo, y validar que no falle en producción.

### 7) Entrega técnica final
- Entregar un `Dockerfile` funcional.
- Exponer el modelo con una API simple en FastAPI para poder correr y evaluar externamente con queries.

### Fecha y seguimiento
- Fecha límite: **viernes 16**.
- Semana siguiente: consulta de dudas para cerrar lo que falte.

Avisen si les queda algo más dando vueltas.
