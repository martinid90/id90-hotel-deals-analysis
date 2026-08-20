# Devoluciones TP1 - Revisión docente detallada

Este archivo resume la revisión de las entregas de TP1 de ambos grupos. Está escrito con dos objetivos:

1. Que cada grupo reciba una devolución clara, formativa y accionable.
2. Que quede documentado qué puntos conviene exigir desde TP2 para evitar problemas en los trabajos siguientes.

La idea central para comunicarles es esta: **en TP1 se evaluaba principalmente el razonamiento exploratorio y la hipótesis de segmentación; desde TP2, además, la entrega tiene que ser reproducible y técnicamente consistente.**

---

## Criterio general para ambos grupos

Hay dos comentarios que aplican a ambos grupos y que conviene marcar una sola vez como criterio común:

- el `reporte_final.md` no es otro notebook, sino una síntesis ejecutiva de la conclusión y la evidencia resumida que la sostiene;
- el mapeo a destino canónico debe hacerse con una lógica común, reproducible y auditada, porque si cada grupo resuelve el mapping de una forma distinta después no estamos comparando los mismos mercados.

En esta primera entrega no se había pedido de forma explícita una estructura cerrada y reproducible. Por eso no tomaría la falta de reproducibilidad perfecta como un error de TP1. Sí lo dejaría marcado como una condición obligatoria desde TP2.

Para TP2, cada grupo debería entregar una carpeta que otra persona pueda ejecutar sin reconstruir pasos a mano. La estructura mínima esperada sería:

```text
entregas/grupo_XX/tp2/
├── README.md
├── reporte_final.md              # síntesis ejecutiva de resultados
├── grupo_XX_tp2.ipynb
├── requirements.txt
├── src/                         # opcional, si separan funciones auxiliares
│   └── ...
├── data/                        # solo datos livianos o muestras
│   └── sample_*.csv.gz
└── outputs/                     # solo outputs necesarios para revisar
```

El `README.md` debería decir:

- cuál es el notebook principal;
- qué datos necesita;
- qué archivos no se suben por peso y dónde deben ubicarse;
- cómo instalar dependencias;
- cómo ejecutar el notebook;
- qué supuestos metodológicos tomaron;
- cuál es la conclusión final;
- qué limitaciones quedan abiertas.

Además del notebook técnico, les pediría un `reporte_final.md`. El notebook puede contener exploración, pruebas descartadas, chequeos y código. El reporte final tiene otra función: **comunicar rápido la conclusión y la evidencia mínima que la sostiene**, como si lo leyera una persona con poco tiempo que necesita entender qué decisión metodológica tomaron.

Esto no es pedir menos análisis. Es pedir mejor comunicación del análisis. En un trabajo real, muchas veces quien toma la decisión no va a revisar todos los notebooks, todas las pruebas descartadas ni todos los gráficos exploratorios. Va a necesitar entender en pocos minutos qué pregunta respondieron, qué encontraron, qué recomiendan y con qué evidencia lo sostienen. Por eso el reporte final debería entrenar justamente esa capacidad: separar lo importante de lo accesorio y transformar un análisis largo en una conclusión defendible.

Estructura sugerida de `reporte_final.md`:

```text
# TP2 - Reporte final

## Pregunta de análisis
¿Qué problema concreto estamos resolviendo?

## Conclusión ejecutiva
En 5-8 líneas: qué contexto proponen y por qué.

## Segmentación propuesta
Ejemplo: destino canónico x mes x duración de estadía.

## Evidencia principal
Solo los gráficos/tablas necesarios para sostener la conclusión.

## Decisiones descartadas
Qué variables evaluaron y por qué no entran al contexto final.

## Cobertura y confianza
Cuántos contextos quedan con datos suficientes y qué demanda cubren.

## Limitaciones
Qué supuestos quedan abiertos.

## Próximos pasos
Qué queda listo para TP3.
```

Este reporte no debería ser una copia de todos los resultados del notebook. Debería ser una síntesis: pregunta, respuesta, evidencia y limitaciones.

Cada gráfico o tabla que entre al `reporte_final.md` debería tener una función clara: responder una pregunta de análisis, sostener una conclusión o justificar una decisión metodológica. Si un gráfico no cambia la conclusión, no hace falta ponerlo en el reporte final; puede quedar en el notebook técnico como exploración.

La lógica del reporte debería ser:

```text
pregunta de análisis -> evidencia resumida -> conclusión -> decisión metodológica
```

Por ejemplo, si la conclusión es que el contexto debe ser `destino x mes`, el reporte no debería mostrar todos los cruces posibles. Debería mostrar la evidencia mínima que demuestra que destino y mes agregan información útil, cuánta demanda queda en contextos con soporte suficiente y qué variables se decidieron dejar afuera.

Aunque esto lo dejaría como requisito formal desde TP2, también les sugeriría rehacer el cierre de TP1 en este formato. Ya tienen los datos procesados y los análisis principales; lo que falta es transformar eso en una presentación final breve: **cuál fue la conclusión obtenida y cuál es la evidencia mínima que la demuestra**.

Un ejemplo de ejecución verificable:

```bash
cd entregas/grupo_XX/tp2
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
jupyter nbconvert --execute --to notebook --output /tmp/grupo_XX_tp2_check.ipynb grupo_XX_tp2.ipynb
```

No hace falta que usen exactamente esos comandos, pero sí tiene que existir una forma equivalente de reproducir la entrega.

### Puntos conceptuales que hay que reforzar desde TP2

Hay cuatro temas que aparecen en ambas entregas y que pueden generar errores grandes en TP2 y TP3 si no se corrigen ahora.

#### 1. Unidad de análisis, noches y `count_repeated`

Para TP2 les pediría que definan con precisión qué representa una fila en cada etapa del análisis:

- una búsqueda original;
- una noche pagada dentro de una estadía;
- una búsqueda ponderada por `count_repeated`;
- un contexto agregado de baseline.

Esto no significa que esté mal desagregar una búsqueda en noches. Al contrario: si quieren estudiar estacionalidad, día de la semana, fines de semana o cruces de mes, **lo correcto es trabajar a nivel noche pagada**. Por ejemplo, una búsqueda del 10/11 al 14/11 contiene las noches del 10, 11, 12 y 13. Esa desagregación permite capturar variabilidad de calendario que se pierde si solo se mira `date_start`.

Lo importante es aclarar qué se está contando y con qué peso:

- si estoy contando búsquedas, la fila original cuenta una vez;
- si estoy analizando noches, la estadía se reparte en varias noches pagadas;
- si uso `count_repeated`, estoy ponderando por cuántas veces se repitió esa búsqueda agregada;
- si calculo baselines, estoy agregando todo eso por destino, mes, semana, duración, etc.

`count_repeated` viene del dataset original y, según la descripción del problema, representa cuántas veces se repitió una búsqueda con las mismas características. Por lo tanto, **sí debería considerarse** cuando quieran aproximar volumen real de demanda. Lo que no conviene es mezclarlo sin explicarlo con el conteo de filas únicas o con el conteo de noches expandidas.

Ejemplo simple:

```text
1 fila original
nights = 4
count_repeated = 100
```

Esa fila puede leerse de distintas maneras:

- 1 búsqueda agregada;
- 4 noches pagadas;
- 100 repeticiones de esa búsqueda;
- 400 noches ponderadas si multiplico noches por repeticiones.

Ninguna lectura es automáticamente incorrecta. El problema sería reportar "400 observaciones" sin aclarar que son noches ponderadas y no 400 búsquedas independientes.

Cómo deberían trabajarlo para TP2:

1. Partir de la fila original y validar datos básicos: fechas, noches, ocupación, precio.
2. Normalizar el precio a una unidad comparable, por ejemplo precio por habitación-noche-persona.
3. Si van a estudiar calendario, desagregar a noches pagadas generando exactamente `nights` filas, no incluyendo el checkout.
4. Mantener `count_repeated` como columna de peso, no necesariamente duplicar físicamente la fila 100 veces.
5. Para estadísticas de mercado, reportar siempre dos cantidades:
   - `n_records`: cantidad de filas originales o noches desagregadas sin ponderar;
   - `demand_weight`: suma de `count_repeated`, o suma de noches ponderadas si están trabajando a nivel noche.
6. Si no quieren asumir que `count_repeated` equivale a búsquedas independientes, pueden usar análisis no ponderado como sensibilidad, pero tienen que decirlo explícitamente.

Ejemplo de media ponderada:

```text
Fila A: price_std = 100, count_repeated = 1
Fila B: price_std = 200, count_repeated = 9
```

Media sin ponderar:

```text
(100 + 200) / 2 = 150
```

Media ponderada por demanda:

```text
(100*1 + 200*9) / (1 + 9) = 190
```

La segunda media representa mejor lo que vio la demanda agregada. La primera representa mejor la diversidad de combinaciones únicas. Ambas pueden ser útiles, pero responden preguntas distintas.

Consecuencia futura: si no fijan esta definición, el criterio de "mínimo 30 observaciones" puede quedar inflado o mezclado. Un baseline puede parecer confiable porque tiene mucho volumen ponderado, pero en realidad venir de muy pocas combinaciones originales. Para TP3 eso importa porque la confianza del algoritmo depende directamente de esa referencia histórica.

#### 2. Segmentos de precio como limitación aceptable de los datos

Quiero aclarar bien este punto: con los datos disponibles actualmente, usar una categoría construida desde el precio puede ser una limitación aceptable del enfoque, no un error. No tenemos estrellas del hotel, amenities, marca, tipo de alojamiento ni un identificador claro de categoría hotelera. Entonces es razonable construir un proxy de gama usando el precio.

Lo que hay que cuidar es cómo se usa después. No es lo mismo usar `price_bucket` para entender la estructura del mercado en TP1 que usar el precio observado en TP3 para decidir el bucket y luego evaluar ese mismo precio contra ese bucket.

El posible problema aparece si el precio participa dos veces:

1. define el grupo de comparación;
2. se evalúa contra ese mismo grupo.

Ejemplo: si llega un precio muy barato para un destino y lo clasifico como `low`, después lo comparo contra el histórico de precios `low`. En ese caso tal vez deje de parecer una oferta, porque lo comparé contra otros precios bajos.

Consecuencia futura: el algoritmo puede perder sensibilidad para detectar ofertas dentro de un mercado. No significa que haya que descartar `price_bucket`, pero sí que hay que presentarlo como una decisión metodológica con limitaciones.

Para TP2/TP3 les pediría que, si mantienen `price_bucket`, expliquen:

- si lo usan solo como análisis descriptivo;
- si lo usan como parte del baseline;
- cómo se calcula sin mirar indebidamente el precio que luego se quiere clasificar;
- qué cambia si comparan resultados con y sin `price_bucket`.

* **Esto es para que lo entiendan y reporten como limitacion!**

#### 3. Fecha de check-in, noche pagada y checkout

En los datos, `date_end - date_start == nights`. Eso normalmente significa que `date_end` es la fecha de checkout, no una noche pagada. Por ejemplo:

```text
date_start = 2024-03-26
date_end   = 2024-03-30
nights     = 4
```

Las noches pagadas son 26, 27, 28 y 29. El 30 es checkout. Si se usa `pd.date_range(start=date_start, end=date_end)`, se generan 5 fechas, no 4.

Consecuencia futura: si expanden fechas de forma inclusiva, sobrecuentan una noche por estadía. Eso afecta el peso de las estadías largas, la distribución por día de semana, los cruces por mes y semana del mes, y puede inflar artificialmente la cantidad de observaciones por contexto.

Para TP2 tienen que elegir una definición:

- si el contexto temporal es el check-in, usen `date_start`;
- si el contexto temporal son las noches pagadas, expandan `0..nights-1`;
- si el contexto es la estadía completa, definan una regla para estadías que cruzan mes o semana.

#### 4. Mapeo a destino canónico y medición de coverage

Usar `destination_with_nearest.csv` como referencia para construir `destination_final` y `destination_name` está bien si esa fue la referencia indicada para el TP. No marcaría ese enfoque como error. Lo que sí hay que exigir desde TP2 es que el merge sea reproducible, cubra los formatos reales del archivo y reporte coverage.

Después de revisar el repositorio de `destination-recommender` y el de `hotel-recommender`, la aclaración importante es esta: el archivo `data/destination_with_nearest.csv` de este TP es el mismo que usa `hotel-recommender-trainer`, pero el input que estamos intentando mapear no está construido con los mismos campos. En `hotel-recommender-trainer` el merge se hace con:

```text
reference = hotel_country_dwh - hotel_state_dwh - hotel_city_dwh
city      = hotel_city_dwh
```

Sobre el archivo de bookings reducido de ese repo, ese merge da 99.95% de cobertura. Eso confirma que el lookup funciona cuando se lo alimenta con los campos DWH normalizados para los que fue construido.

En cambio, los históricos del TP salen de `analytic.customer_shopping_model` unido a `analytic.hotel_city_location` y traen `city`, `state`, `country`, `country_code`. En esos CSV hay casos donde `city` parece barrio, distrito, localidad chica, CDP o county, y `state` contiene el mercado más amplio. Por eso no alcanza con decir "los archivos vienen del mismo origen": el CSV de mapping puede ser el mismo, pero si la geografía que entra al merge está en otro nivel de granularidad, el match exacto cambia.

El problema que apareció mezcla dos cosas distintas:

1. **Bug o limitación de implementación:** la función original arma una sola clave `country_code - state_code - city`. En los históricos `country_code` viene en minúscula (`us`, `kr`) y el mapping usa mayúscula (`US`, `KR`). Además, el mapping no tiene siempre tres partes: también hay claves como `KR - Busan` o `AR - Buenos Aires`.
2. **Limitación real del extract actual:** aun con un pretratamiento razonable, algunas geografías del TP no existen como `(reference, city)` exacto en el lookup porque están a otro nivel administrativo o tienen variantes de nombre.

Dicho más directo: el error de mapping no fue usar `destination_with_nearest.csv`; eso estaba bien. El error fue asumir que había una única clave válida y que bastaba con armar `country_code - state_code - city`. Esa regla pierde matches por mayúsculas/minúsculas, por países sin estado, por referencias de dos partes y por diferencias de granularidad entre `hotel_city_location` y los campos DWH normalizados del recomendador.

Para dejarles una referencia concreta, armé el notebook `notebooks/tp2_mapping_merge_referencia.ipynb` y el script `scripts/destination_mapping_preprocess.py`. El notebook muestra cómo ejecutar el merge y medir coverage; el script deja la lógica reutilizable para que no haya una función distinta en cada entrega.

El pretratamiento recomendado hace:

- normalización de mayúsculas, acentos y espacios;
- conversión de estados de Estados Unidos de nombre completo a código;
- claves exactas `country - state_code - city`, `country - state_name - city` y `country - city`, siempre contra `(reference, city)`;
- alias puntuales auditables, como `USA`, territorios de Estados Unidos y sufijo `CDP`;
- fallback `country - state` solo para países no-US, marcado como `non_us_state_as_place`, porque en estos históricos a veces `city` es un barrio/distrito y `state` contiene el mercado turístico;
- una columna `match_level` para saber exactamente qué regla produjo cada match.

No recomiendo prender automáticamente fallbacks más amplios, como `country - state` para Estados Unidos o `(country, city)` ignorando el estado. Esos fallbacks pueden servir para generar candidatos de auditoría, pero no como asignación automática de `nearest_destination_id`.

La comparación sobre todo el histórico disponible queda así:

```text
Estrategia                                           Coverage filas   Coverage demanda
Función original del repo                                 0.0%              0.0%
Solo upper + state/city                                  33.0%             46.6%
Cascada estricta reference/city                          63.3%             76.8%
Pretratamiento recomendado                               69.0%             80.5%
Fallback país-ciudad ignorando estado                    70.4%             82.1%   no recomendado sin auditar
```

Con el pretratamiento recomendado, la corrida validada del script/notebook da:

```text
filas mapeadas:                     3,558,663 / 5,158,190 = 68.991%
demanda mapeada:                   29,916,231 / 37,167,072 = 80.491%
geografías crudas únicas mapeadas:     14,767 / 41,535 = 35.553%
```

Cómo leer estos números:

- **Filas mapeadas:** son filas del CSV histórico que lograron recibir un `nearest_destination_id` con la estrategia de mapping. En estos archivos, una fila no necesariamente es una búsqueda individual: es una combinación agregada de geografía, fechas, pasajeros, habitaciones, noches y estadísticas de precio. Por eso este porcentaje mide cobertura sobre el dataset de trabajo, no volumen real de demanda.
- **Demanda mapeada:** es la suma de `count_repeated` de las filas mapeadas. Esta métrica pesa más a las filas que representan búsquedas repetidas. Que la demanda mapeada sea 80.5% mientras las filas mapeadas son 69.0% significa que las geografías que sí logramos mapear concentran más volumen que muchas geografías no mapeadas de baja frecuencia.
- **Geografías crudas únicas mapeadas:** son combinaciones únicas de `country_code`, `country`, `state` y `city` que lograron recibir un destino canónico. Este número no mide demanda ni búsquedas; mide variedad de nombres/lugares crudos que aparecen en el input. Por ejemplo, `Miami Beach, Florida` cuenta como 1 geografía, pero también cuenta como 1 geografía una localidad muy chica que aparece pocas veces. El porcentaje es más bajo, 35.6%, porque existe una cola muy larga de localidades, barrios, distritos, counties, CDP o nombres alternativos con pocas filas. Esto no significa que se pierda 64.4% de la demanda: significa que muchas geografías únicas son raras o poco frecuentes.
- **No-match:** son filas que, después del pretratamiento recomendado, siguen sin `nearest_destination_id`. No necesariamente son datos inválidos. Pueden ser zonas turísticas, barrios, variantes administrativas, países/territorios escritos de otra forma o filas con geografía nula. Lo importante es que queden marcadas como `match_level = no_match` para auditarlas, no esconderlas bajo `city` como si fueran destinos canónicos.

Por eso, para evaluar cobertura del análisis de precios miraría principalmente **demanda mapeada** y luego **filas mapeadas**. La métrica de geografías crudas únicas sirve como control de calidad del preprocesamiento: muestra cuánta cola de nombres/lugares queda por auditar, pero no debe leerse como "solo cubrimos 35.6% del negocio".

Entonces la conclusión correcta es: **el problema inicial era real, pero no significaba que el archivo de referencia no sirviera**. La función original fallaba por formato y por asumir una sola estructura de clave. Al corregir eso y agregar pretratamiento controlado, se recupera gran parte de la demanda. Lo que queda sin matchear sí es una limitación real del extract actual y hay que medirla.

Con el pretratamiento recomendado, el 31.0% de filas queda explícitamente como `match_level = no_match`. No desaparece: si una entrega no lo muestra, probablemente es porque reportó solo los destinos mapeados o porque después usó la ciudad cruda como fallback y eso lo hizo parecer un destino válido. Sobre todo el histórico, ese `no_match` representa 1,599,527 filas y 7,250,841 de demanda ponderada, es decir 19.5% de la demanda total.

Ejemplos principales de `no_match` por demanda:

```text
country_code   country                    state          city                         filas   demanda
us             United States of America   Florida        Miami Beach                  19706   473159
us             United States of America   Nevada         Winchester                   16900   386531
NaN            NaN                        NaN            NaN                          26649   373051
us             United States of America   California     Lomita Park                  11188   279213
us             United States of America   Washington     SeaTac                        8200   188259
us             United States of America   Florida        Dr. Phillips                 14201   180182
us             United States of America   Puerto Rico    San Juan Antiguo             11875   168976
us             United States of America   Illinois       Norridge                      8453   159172
nl             Netherlands                NaN            NaN                          13494   113172
us             United States of America   Hawaii         Kahaluu-Keauhou CDP            9335    96614
us             United States of America   Hawaii         Maui County                  12220    85105
```

Estos ejemplos ayudan a interpretar el problema. Algunos son zonas turísticas que probablemente podrían consolidarse a un mercado mayor (`Miami Beach`, `Dr. Phillips`, `SeaTac`). Otros son barrios, CDP, counties, territorios o geografías nulas. Pero no conviene asignarlos automáticamente sin evidencia, porque los fallbacks amplios pueden equivocarse fuerte. Por ejemplo, un fallback `country - state` puede mandar ciudades del estado de Washington a `Washington DC`, y un fallback por `(country, city)` puede mapear `Winchester, Nevada` contra otro `Winchester` de Kentucky, Tennessee o Virginia. Por eso no alcanza con mirar el porcentaje global: hay que listar los no-matcheados por demanda y decidir cuáles requieren corrección, cuáles pueden usar fallback auditado y cuáles conviene excluir o dejar como ciudad cruda.

Si para TP2 queremos garantizar una cobertura parecida a la del recomendador, la solución correcta no es inventar fallbacks cada vez más amplios. La solución es re-extraer los históricos con los mismos campos DWH usados por el pipeline (`hotel_country_dwh`, `hotel_state_dwh`, `hotel_city_dwh`) o regenerar el lookup desde las coordenadas/campos de estos históricos. Mientras trabajen con los CSV actuales, la exigencia debe ser: usar el pretratamiento de referencia, reportar coverage y auditar la cola no mapeada.

Para TP2 deberían reportar siempre:

- coverage por filas;
- coverage ponderado por `count_repeated`;
- coverage por geografías únicas;
- cantidad de filas por `match_level`;
- principales geografías no matcheadas por demanda;
- qué fallback usan cuando no hay destino canónico.

No deberían modificar manualmente el dataset para que "entre" en una clave. Deberían construir la clave siguiendo los formatos del mapping y dejar trazabilidad de qué regla produjo cada match.

---

# Grupo 1

## Lectura general

El trabajo del Grupo 1 tiene una buena intención analítica. Se nota que entendieron el problema de fondo: antes de clasificar si un precio es bueno o malo, hay que decidir contra qué mercado y bajo qué contexto se lo compara.

También hay puntos valiosos:

- detectaron un problema real en el mapeo de destinos por formato de `country_code`;
- compararon destino contra país y mostraron por qué país puede ser una mala unidad;
- miraron heterogeneidad por destino y no solo promedios globales;
- identificaron que el efecto fin de semana no es homogéneo entre destinos;
- no se quedaron solamente con correlaciones lineales para `nights`;
- llegaron a una hipótesis final clara.

La hipótesis final propuesta fue:

```text
contexto = destino x price_bucket x mes
```

con día de semana como chequeo condicional. Como hipótesis exploratoria de TP1 es razonable. El problema es que antes de convertirla en pipeline para TP2 hay varias cosas que deben tener en cuenta.

---

## Grupo 1 - Observaciones detalladas

### 1. La carga de datos parece usar solo un archivo histórico

**Qué observé**

El notebook copia archivos de 2024 y 2025, pero después carga:

```python
df_completo = pd.read_csv(archivos[0])
df_raw = df_completo.sample(n=100_000, random_state=42)
```

Eso significa que toma una muestra aleatoria de un solo archivo, el primero de la lista ordenada. En la práctica, probablemente sea solo `datos_historicos_2024.csv`.

**Por qué es un problema**

Muchas conclusiones del problema dependen de patrones estacionales y de estabilidad temporal. Si el análisis usa solo un año, no se puede generalizar al período completo 2024-2025. Para TP1 exploratorio puede servir como primera aproximación, pero si la conclusión pretende definir contexto para el proyecto, debería apoyarse en ambos años o aclarar explícitamente que es una hipótesis tomada sobre una muestra parcial.

**Consecuencia para TP2/TP3**

Un baseline entrenado con un solo año puede capturar particularidades de ese año y no el patrón general. Si luego se usa para detectar ofertas en otro período, puede clasificar como "oferta" algo que en realidad es un cambio normal de temporada o de año.

**Qué deberían ajustar**

Para TP2 deben indicar explícitamente:

- si trabajan con 2024, 2025 o ambos;
- si usan muestra, cómo se tomó;
- si la muestra es aleatoria y con qué semilla;
- si las conclusiones aplican a todo el dataset o solo a la muestra.

Si usan ambos años, deberían concatenar los archivos antes de muestrear, muestrear de forma balanceada por año o directamente correr el análisis sobre todos los datos cuando sea computacionalmente posible. Las conclusiones finales del TP2 deberían salir del dataset completo o de una muestra cuya representatividad esté demostrada.

---

### 2. La expansión temporal es necesaria, pero debe representar noches pagadas

**Qué observé**

El notebook usa `expand_dates_dataframe(df)`. En las funciones del repo, esa expansión usa un rango inclusivo de `date_start` a `date_end`.

En los datos, `date_end - date_start == nights`. Entonces, si una estadía tiene 4 noches, el rango inclusivo produce 5 fechas.

**Por qué es un problema**

La idea de expandir por fecha es buena y está alineada con el criterio común: para estudiar estacionalidad, día de semana y fines de semana conviene trabajar a nivel noche pagada. El problema específico es que la función inclusiva parece sumar el checkout como si fuera una noche adicional.

**Consecuencia para TP2/TP3**

Esto puede distorsionar:

- promedios por día de semana;
- efectos de fin de semana;
- mes y semana del mes;
- cantidad de observaciones por contexto;
- confianza de los baselines.

Además, las estadías largas quedan más sobreponderadas de lo que corresponde.

**Qué deberían ajustar**

Para TP2 deberían reemplazar o corregir esa función para generar exactamente `nights` fechas:

```python
offsets = range(nights)
date = date_start + offset
```

No deberían incluir `date_end` salvo que justifiquen que representa una noche observada, cosa que no parece consistente con la columna `nights`. Si vuelven a calcular efectos por mes, semana o día de semana, deberían hacerlo con esta corrección aplicada.

Ejemplo:

```text
date_start = 10/11
date_end   = 14/11
nights     = 4
count_repeated = 100
```

Noches pagadas:

```text
10/11, 11/11, 12/11, 13/11
```

Cada una de esas noches conserva `count_repeated = 100`. Si luego calculan una media por día de semana o por mes, pueden usar ese valor como peso.

---

### 3. `price_bucket` es una limitación razonable de los datos

**Qué observé**

El grupo clasifica observaciones en `low`, `medium` y `high` según percentiles del precio normalizado dentro de cada destino. Luego esa variable aparece como una de las dimensiones más fuertes para reducir dispersión y queda incluida en la hipótesis final.

**Cómo lo interpretaría**

Aplica el criterio común explicado al inicio: `price_bucket` es una limitación aceptable de los datos, no un error. No tenemos estrellas del hotel, marca, amenities, tipo de alojamiento ni una categoría hotelera confiable. Entonces usar precio como proxy de gama puede ser razonable para TP1.

Lo que deberían declarar es la limitación: el mismo precio que ayuda a construir el segmento también está relacionado con lo que después queremos evaluar. Por eso `price_bucket` puede ser útil para explorar estructura de mercado, pero debe presentarse como proxy imperfecto, no como una categoría real del alojamiento.

**Qué deberían ajustar**

Para TP2 deberían mostrar explícitamente qué cambia al usarlo y qué se pierde o gana metodológicamente.

Una forma razonable de avanzar sería reportar ambos escenarios:

```text
baseline A = destino x mes
baseline B = destino x mes x price_bucket
```

y discutir qué se gana y qué se pierde en cobertura, dispersión y sensibilidad para detectar ofertas.

---

### 4. La regresión no termina de aportar a la pregunta principal

**Qué observé**

El notebook incluye regresiones OLS con muchas variables, incluyendo dummies por destino. Los R2 reportados son bajos en varios modelos, por ejemplo alrededor de 0.014 o 0.024, y los residuos muestran una distribución muy problemática.

**Por qué es un problema**

No queda claro cuál era el objetivo de esa regresión. Si la pregunta es "qué dimensiones conviene usar para definir contexto", una regresión con muchas dummies de destino sobre un dataset muy heterogéneo no necesariamente ayuda. Incluir una variable por destino puede absorber diferencias geográficas, pero no necesariamente produce una conclusión clara sobre cómo conviene segmentar ni sobre qué decisión tomar.

Además, con muchos registros, casi cualquier coeficiente puede aparecer como estadísticamente significativo. Un p-value bajo no alcanza para concluir que una variable es importante para el problema. Hay que mirar también tamaño del efecto, varianza explicada, estabilidad del resultado y sentido de negocio.

En los modelos reportados, los R2 bajos indican que queda una cantidad muy grande de variabilidad sin explicar. Eso no invalida automáticamente la regresión, pero sí limita mucho la interpretación. Si el modelo explica una parte mínima del precio, no conviene usarlo como evidencia fuerte para decidir el contexto final.

También hay que tener cuidado con los supuestos de fondo de una OLS. Antes de interpretar coeficientes y p-values como evidencia, deberían revisar al menos:

- residuos: si están centrados, si tienen patrones sistemáticos y si aparecen colas muy pesadas;
- heterocedasticidad: si la varianza del error cambia según precio, destino, mes o duración;
- outliers e influencia: si pocos precios extremos están empujando coeficientes;
- no linealidades: si la relación entre precio y variables como `nights` o fecha no es lineal;
- multicolinealidad o redundancia: si variables de destino, mes, bucket y otros controles se pisan entre sí;
- extrapolación: si las conclusiones se aplican solo a los destinos frecuentes observados o si se están generalizando a mercados con poca información.

Este último punto es importante: una regresión puede describir patrones promedio del dataset usado, pero no necesariamente permite extrapolar a destinos poco frecuentes, meses con poca cobertura o combinaciones nuevas de contexto. Para TP3, ese tipo de extrapolación puede hacer que el algoritmo parezca más confiable de lo que realmente es.

Si querían usar una regresión para sustentar la segmentación, hubiese sido más informativo plantearla de forma más dirigida. Por ejemplo:

- comparar modelos agregando bloques de variables y reportar ganancia incremental de cada bloque;
- reducir primero la dimensión geográfica, por ejemplo país, región, top destinos vs resto, o grupos de destinos con suficiente volumen;
- usar variables de contexto candidatas y mirar cuánto mejora la explicación al agregarlas;
- reportar métricas fuera de muestra o al menos una comparación simple entre modelos;
- mostrar diagnóstico de residuos antes de interpretar coeficientes;
- interpretar la regresión solo como apoyo, no como evidencia central.

**Consecuencia para TP2/TP3**

Podrían elegir variables por p-value en vez de elegirlas por capacidad real de mejorar la comparación de precios. Eso llevaría a contextos más complejos pero no necesariamente mejores.

**Qué deberían ajustar**

Para este proyecto, yo priorizaría métricas más conectadas con el problema:

- reducción de dispersión dentro de grupo;
- cobertura de contextos con suficiente muestra;
- estabilidad temporal;
- desempeño de un baseline simple;
- sensibilidad de clasificaciones ante cambios de segmentación.

La regresión puede quedar como análisis auxiliar, pero no debería ocupar el centro si no responde directamente por qué el contexto final elegido es el mejor. Para sostener `destino x price_bucket x mes`, sería más fuerte mostrar una tabla de decisión breve: qué aporta destino, qué aporta mes, qué aporta `price_bucket`, qué cobertura queda y qué variables se descartan.

---

# Grupo 2

## Lectura general

El Grupo 2 presentó un análisis ambicioso y bastante avanzado para TP1. Se nota que intentaron pasar de exploración a una propuesta concreta de contexto para comparar precios.

La hipótesis final propuesta fue:

```text
contexto = destination_final x month x week_in_month x stay_duration
```

con `price_bucket` como dimensión opcional. Esta hipótesis está razonablemente apoyada por análisis de homogeneidad, cobertura de baselines e inspección interanual.

Para TP2 no les pediría "más gráficos", sino cerrar algunos puntos que sí afectan la validez de las conclusiones.

---

## Grupo 2 - Observaciones detalladas

### 1. Muestras para explorar, dataset completo para concluir

**Qué observé**

El notebook dice que trabaja con una muestra representativa de 300.000 filas. Pero el código tiene distintos caminos:

```python
if DB_PATH.exists():
    ... ABS(RANDOM()) % 15 = 0 LIMIT SAMPLE_SIZE
elif hist_files:
    pd.read_csv(f, nrows=per_file)
elif sample_gz_path.exists():
    pd.read_csv(sample_gz_path)
```

Si existen los CSV crudos, se leen las primeras `nrows` filas de cada archivo. Eso no es una muestra aleatoria. Si existe la base SQLite, se usa `RANDOM()` sin semilla fija. Solo el archivo `sample_data_300k.csv.gz` parece una muestra cerrada.

**Por qué es un problema**

Usar muestras no está mal. Para explorar datos, detectar patrones, hacer pruebas visuales o acelerar gráficos, es totalmente razonable. El punto es separar exploración de conclusión final.

Si una figura o tabla se usa para justificar la segmentación final, debería salir del dataset completo o de una muestra cuya representatividad esté demostrada. Si se toman las primeras filas de cada CSV, puede haber sesgo por el orden del archivo. Si se usa `RANDOM()` sin semilla, el resultado puede cambiar entre corridas.

**Consecuencia para TP2/TP3**

Las conclusiones sobre estacionalidad, destinos principales, cobertura de baselines y homogeneidad pueden cambiar según qué fuente de datos exista en la máquina donde se ejecuta el notebook. Eso no invalida la exploración, pero sí debilita una conclusión si no queda claro de dónde salió.

**Qué deberían ajustar**

Para TP2 les pediría:

- usar muestra para exploración rápida, claramente identificada como muestra;
- hacer las tablas y gráficos finales de conclusión con todo el dataset cuando sea computacionalmente posible;
- si una conclusión se apoya en una muestra, documentar cómo se tomó, con qué semilla y qué tan parecida es al total en año, mes, destino y país.

La idea no es prohibir muestras. La idea es que el lector sepa qué resultados son exploratorios y cuáles sostienen la conclusión final.

---

### 2. Hay un error en el etiquetado de días de semana

**Qué observé**

El notebook calcula:

```python
df['day_of_week'] = df['date_start'].dt.dayofweek
```

En pandas, `dt.dayofweek` devuelve:

```text
0 = lunes
1 = martes
2 = miércoles
3 = jueves
4 = viernes
5 = sábado
6 = domingo
```

Pero el notebook define:

```python
dias_nombre = {0: 'Dom', 1: 'Lun', 2: 'Mar', 3: 'Mié', 4: 'Jue', 5: 'Vie', 6: 'Sáb'}
```

Es decir, todos los días quedan desplazados.

**Por qué es un problema**

Este es un error concreto de interpretación. Si el lunes se etiqueta como domingo, cualquier gráfico o conclusión por día de semana queda mal nombrado.

**Consecuencia para TP2/TP3**

Si `day_of_week` entra al contexto o al algoritmo, el modelo puede aprender patrones con etiquetas equivocadas. También puede llevar a conclusiones falsas como "sábado es más caro" cuando en realidad se está mirando otro día.

**Qué deberían ajustar**

Corregir el diccionario:

```python
dias_nombre = {
    0: 'Lun',
    1: 'Mar',
    2: 'Mié',
    3: 'Jue',
    4: 'Vie',
    5: 'Sáb',
    6: 'Dom',
}
```

Y volver a revisar todas las conclusiones sobre día de semana y fin de semana.

---

### 3. Hay inconsistencia entre check-in y noches de estadía

**Qué observé**

En el notebook principal, las variables temporales se construyen con `date_start`:

```python
df['month'] = df['date_start'].dt.month
df['week_in_month'] = ...
df['day_of_week'] = df['date_start'].dt.dayofweek
```

Pero el pipeline auxiliar tiene una función que expande fechas desde `date_start` hasta `date_end` de forma inclusiva. Como en los datos `date_end - date_start == nights`, esa expansión genera una fila de más por estadía si `date_end` es checkout.

**Por qué es un problema**

El punto específico no es repetir la discusión general sobre noches, sino marcar que notebook y pipeline no están usando exactamente la misma unidad temporal. Uno parece analizar fecha de inicio de estadía; el otro intenta analizar noches individuales.

**Consecuencia para TP2/TP3**

Puede pasar que las conclusiones del notebook no coincidan con los baselines generados por el pipeline. Por ejemplo, una estadía que empieza el 30 de enero y termina en febrero puede contarse de manera diferente según la implementación.

**Qué deberían ajustar**

Para TP2 deben elegir una sola regla temporal y aplicarla en ambos lugares. Si la segmentación final sigue siendo `month x week_in_month x stay_duration`, esas variables tienen que calcularse con la misma definición en el notebook exploratorio y en el pipeline que genera baselines.

---

### 4. Algunas afirmaciones centrales deben coincidir con los outputs

**Qué observé**

Hay algunas diferencias entre texto, README y salidas guardadas. No lo marcaría como un problema central del TP1, pero sí como algo a corregir antes de armar el reporte final.

El comentario es simplemente este: **cuiden que los números del texto coincidan con los outputs visibles**. Si un número sostiene una conclusión, tiene que poder encontrarse en una celda ejecutada o en un archivo de salida final. Si cambió la corrida, actualicen la narrativa.

**Qué deberían ajustar**

Antes de entregar el reporte final, hacer una pasada de consistencia:

- cada número importante del texto debe salir de una celda visible;
- si cambió la corrida, actualizar la conclusión;
- si hay versiones distintas, dejar solo la que sostiene el resultado final.

---

### 5. Registros, demanda ponderada y noches deben quedar separados

**Qué observé**

En `calculate_baselines`, el pipeline agrupa por contexto y calcula:

```text
count_obs     = suma de count_repeated
count_records = cantidad de filas originales en el grupo
```

Esto no está necesariamente mal. De hecho, usar `count_repeated` como peso es razonable si queremos aproximar volumen de demanda. El punto es que el nombre `count_obs` puede confundirse: no representa cantidad de filas independientes, sino demanda ponderada.

**Por qué es un problema**

Para TP2, el pipeline debería dejar claro el orden de construcción de la unidad de análisis:

1. partir de la fila original;
2. si se analiza calendario, expandir a **noches pagadas**;
3. conservar `count_repeated` como peso de esa noche/fila;
4. calcular estadísticas ponderadas usando ese peso;
5. reportar por separado cuántas filas/noches reales hay y cuánta demanda ponderada representan.

Si después usan `N >= 30` como criterio de confiabilidad, tienen que aclarar qué significa ese `N`: ¿30 filas originales?, ¿30 noches?, ¿30 unidades de demanda ponderada? No son equivalentes.

**Consecuencia para TP2/TP3**

Un baseline puede parecer confiable por volumen de demanda, pero estar basado en muy pocos contextos únicos. Eso puede inflar la confianza y reducir artificialmente la incertidumbre.

**Qué deberían ajustar**

Para TP2 deberían conservar ambas métricas con nombres que no se confundan:

- `n_records` o `n_nights`: cantidad de filas reales usadas en el contexto, según la unidad elegida;
- `demand_weight`: suma de `count_repeated`;
- `weighted_nights`, si expanden a noches y quieren medir volumen de noches ponderadas.

Si el criterio de confiabilidad usa demanda ponderada, deberían decirlo explícitamente. Si además exigen un mínimo de registros reales, mejor todavía.

---

### 6. El SNR está bien usado, pero debe mostrarse junto al soporte de datos

**Qué observé**

SNR significa **Signal-to-Noise Ratio**, o relación señal-ruido. En el notebook lo calculan como:

```text
SNR = varianza entre grupos / varianza dentro de los grupos
```

Interpretación:

- si el SNR sube, los grupos que formé son más distintos entre sí y más homogéneos internamente;
- para este problema, eso sugiere que la segmentación ayuda a comparar precios dentro de contextos más parecidos;
- eso está bien como evidencia de homogeneidad.

En el notebook sí aparece una tabla de SNR donde aumenta al agregar dimensiones:

```text
Solo Destino                         SNR = 0.0893
Destino + Mes                        SNR = 0.1401
Destino + Mes + Semana               SNR = 0.1557
Destino + Mes + Semana + Estadía     SNR = 0.2943
```

Esto está correctamente orientado y sí apoya la hipótesis de contexto más granular. La conclusión `destination_final x month x week_in_month x stay_duration` no parece salir de la nada: está alineada con el análisis de homogeneidad.

**Qué falta para que quede más claro**

Cuando digo "cobertura" acá no me refiero al coverage del mapping ni a si entran todas las filas al dataset. Me refiero a **cuánta demanda queda en contextos confiables** después de segmentar.

Si agrego más dimensiones, normalmente pasa esto:

- mejora la homogeneidad: sube el SNR;
- aumenta la fragmentación: aparecen muchos más contextos;
- algunos contextos quedan con pocas filas o poca demanda.

Entonces, aunque todos los datos tengan una celda asignada, no todos los contextos tienen el mismo nivel de confianza estadística. Por eso conviene mostrar SNR junto con soporte de datos:

```text
Segmentación                         SNR     Contextos   % demanda en contextos confiables
Destino                              ...     ...         ...
Destino + Mes                        ...     ...         ...
Destino + Mes + Semana               ...     ...         ...
Destino + Mes + Semana + Estadía     ...     ...         ...
```

La pregunta que esa tabla responde es: **la segmentación mejora la homogeneidad sin dejar demasiada demanda apoyada en contextos débiles?** Si el SNR sube y además la mayor parte de la demanda queda en contextos con suficiente soporte, la segmentación queda mucho mejor defendida.

---

### 7. Outliers y medias: hace falta una política explícita

**Qué observé**

Acá no digo que esté mal ni que hayan ignorado outliers. De hecho, tienen algunos filtros:

- `validate_data` elimina precios crudos `<= 0` o `> 50.000`;
- en algunos gráficos usan filtros visuales, por ejemplo `price_std < 500`;
- en baselines aplican un piso mínimo al desvío estándar.

El problema es que no queda una política única y explícita para todo el análisis. Además, en los outputs guardados aparecen valores extremos después de normalizar:

- en `market_baselines.csv`, `mean_price_std` llega a valores muy altos;
- `max_price_std` tiene máximos extremadamente grandes;
- incluso aparecen mínimos negativos en `min_price_std`, lo cual debería revisarse porque un precio normalizado negativo no parece interpretable como precio real.

**Por qué es un problema**

Las medias, varianzas y SNR son sensibles a outliers. Si algunos precios extremos vienen de errores de datos, monedas, cargas raras o contextos muy especiales, pueden dominar las métricas. En este trabajo eso importa porque los baselines se apoyan en media y desvío, y el SNR se apoya en varianzas.

**Consecuencia para TP2/TP3**

Los baselines pueden quedar demasiado altos o con desviaciones enormes. Eso haría que pocas cosas parezcan ofertas, o que se clasifiquen mal precios normales.

**Qué deberían ajustar**

Para TP2 deberían definir una política estable:

- filtros por precio total y precio normalizado;
- winsorización o percentiles;
- uso de mediana/IQR además de media/desvío;
- análisis separado de outliers reales vs errores.

---

# Indicaciones comunes para TP2

Les pediría a ambos grupos que lleguen al TP2 con estas decisiones escritas al inicio del notebook:

1. **Unidad de análisis:** búsqueda original, noche pagada, demanda ponderada o contexto agregado.
2. **Fuente de datos:** 2024, 2025, ambos años, muestra o dataset completo.
3. **Muestreo:** si hay muestra, cómo se obtuvo y con qué semilla.
4. **Fecha del contexto:** check-in, noche pagada o estadía completa.
5. **Precio comparable:** fórmula exacta de normalización.
6. **Filtros de calidad:** noches válidas, ocupación válida, precios extremos, nulos.
7. **Mercado geográfico:** destino canónico, ciudad cruda o regla híbrida.
8. **Desagregación temporal:** si estudian calendario, cómo generan noches pagadas y cómo evitan incluir checkout.
9. **Uso de `count_repeated`:** si ponderan estadísticas, cómo calculan medias, conteos y cobertura.
10. **Variables de segmentación:** cuáles entran al baseline y cuáles quedan solo para diagnóstico.
11. **Criterio de confianza:** registros independientes, demanda ponderada, noches ponderadas o una combinación.
12. **Fallbacks:** qué hacen cuando no hay datos suficientes para un contexto.
13. **Reproducibilidad:** comando o pasos para correr todo desde cero.

La consigna para TP2 debería ser: **no alcanza con decir qué segmentación parece buena; tienen que implementarla como una transformación de datos clara, auditable y consistente.**
