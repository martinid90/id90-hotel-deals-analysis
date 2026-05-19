# Hotel Deals Analysis — Sistema de Detección de Ofertas Hoteleras

**Diplomatura en Ciencia de Datos · Proyecto Final**

Sistema para la detección automática de oportunidades de precio en búsquedas hoteleras (ofertas), desarrollada sobre datos históricos de búsquedas de la plataforma ID90Travel.

---

## Tabla de Contenidos

0. [Para Estudiantes — Mentoría DiploDatos 2026](#para-estudiantes--mentoría-diplodatos-2026)
1. [Contexto: ID90Travel y el Problema](#1-contexto-id90travel-y-el-problema)
2. [Objetivo del Proyecto](#2-objetivo-del-proyecto)
3. [Flujo de Trabajo: Scripts y Resultados](#3-flujo-de-trabajo-scripts-y-resultados)
4. [Contenido del Repositorio](#4-contenido-del-repositorio)
5. [Fuentes de Datos Disponibles](#5-fuentes-de-datos-disponibles)
6. [Enfoque Explorado: Aproximación Estadística](#6-enfoque-explorado-aproximación-estadística)
7. [Query de Extracción de Datos](#7-query-de-extracción-de-datos)
8. [Dataset: Descripción del Esquema de Datos](#8-dataset-descripción-del-esquema-de-datos)
9. [Archivo de Normalización de Destinos](#9-archivo-de-normalización-de-destinos)
10. [Pipeline de Procesamiento](#10-pipeline-de-procesamiento)
11. [Datasets Generados (Outputs)](#11-datasets-generados-outputs)
12. [Principales Problemáticas Resueltas](#12-principales-problemáticas-resueltas)
13. [Limitaciones y Alcance del Enfoque Actual](#13-limitaciones-y-alcance-del-enfoque-actual)
14. [Cómo Ejecutar el Proyecto](#14-cómo-ejecutar-el-proyecto)
15. [Ejemplos de Uso de la Aplicación](#15-ejemplos-de-uso-de-la-aplicación)
16. [Extensiones Propuestas](#16-extensiones-propuestas)

---

## Para Estudiantes — Mentoría DiploDatos 2026

Bienvenidos/as a esta mentoría. Este repositorio documenta el objetivo que se persigue en el presente trabajo y combina, en un mismo lugar, un trabajo exploratorio real sobre el problema de clasificación de precios hoteleros desarrollado en ID90Travel. En el repositorio no solo se encontrará el contenido de lo que se pretende en la mentoría, sino que además se incluye una primera versión del análisis realizado, para que sirva como método de inspiración, lineamiento y comparación. El código, el pipeline y los análisis disponibles representan un primer intento de abordar el problema — son material de referencia e inspiración, no una solución definitiva.

El objetivo de la mentoría es que EL grupo explore el problema de forma independiente, comprenda qué funciona y qué no en el enfoque documentado, y proponga su propia solución. El repo existe para que no partan desde cero: los datos son reales, los desafíos técnicos son genuinos y las preguntas sin resolver son las mismas que enfrenta el negocio hoy.

---

### Primeros pasos con el proyecto

**1. Clonar el repositorio**
```bash
git clone https://github.com/martinid90/id90-hotel-deals-analysis.git
cd id90-hotel-deals-analysis
```

**2. Crear y activar el entorno de trabajo (recomendado: conda)**
```bash
conda create -n hotels python=3.11
conda activate hotels
pip install -r requirements.txt
```
> Alternativa con venv: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

**3. Descargar los datos y colocarlos en la carpeta `data/`**

Los archivos de datos históricos están disponibles en Google Drive:
📁 [Descargar datasets → Google Drive](https://drive.google.com/drive/folders/1fNs03vOkkO2mVKibHKLmCbzgyatv1yCd?usp=drive_link)

Descargar los archivos `datos_historicos_*.csv` y colocarlos en la carpeta `data/` del proyecto:

```
id90-hotel-deals-analysis/
└── data/
    ├── datos_historicos_2024.csv      ← descargar de Drive (~300 MB)
    ├── datos_historicos_2025.csv      ← descargar de Drive (~300 MB)
    └── destination_with_nearest.csv   ← ya incluido en el repo
```

**4. Abrir el notebook de ejemplo**
```bash
jupyter notebook exploratory_analysis.ipynb
```

El notebook `exploratory_analysis.ipynb` carga los datos reales, recorre las etapas del pipeline paso a paso y muestra cómo el sistema clasifica un precio.

---

### El problema de negocio

Cada día millones de personas buscan hoteles sin saber si el precio que ven es una oportunidad conveniente, un precio normal o una estafa del proveedor. La pregunta que guía este proyecto es:

> **¿El precio que se muestra para este destino, en estas fechas y para esta configuración de viaje, es una oferta real o no?**

Es muy importante tener en cuenta el concepto que definiremos como **CONTEXTO**: la combinación de factores que determinan la unidad de análisis o granularidad que servirá como base para la comparación — por ejemplo: `mercado × DOW × DOY × hotel_class × ...`

Responder esa pregunta parece simple pero esconde dos subproblemas que son el núcleo de la mentoría:

- **¿Contra qué se compara?** — Para saber si un precio es bajo necesitás un precio de referencia. Pero esa referencia tiene que venir del mismo mercado, en condiciones comparables. Definir qué es "el mismo mercado" y qué son "condiciones comparables" es el desafío central.
- **¿Cómo se detecta?** — Una vez que tenés una referencia histórica, ¿qué método usás para determinar si el precio observado es inusualmente bajo? ¿Estadística descriptiva, inferencia, machine learning?

Las preguntas de investigación a continuación desarrollan estos desafíos en detalle.

---

### Preguntas de investigación

Estas son las preguntas centrales que guiarán la mentoría. No tienen una respuesta única ni correcta — el objetivo es que el grupo las explore con los datos y formule sus propias hipótesis y conclusiones.

#### 1. Definición de mercado: ¿contra qué se compara?

**El problema de la referencia**: para saber si un precio es una oferta necesitás un precio de referencia del mismo mercado. Un hotel en Las Vegas no compite con uno en Orlando — aunque ambos sean destinos turísticos norteamericanos. Pero, ¿Las Vegas y Henderson (ciudad a 30 km) son el mismo mercado? ¿Y Las Vegas y Miami? La pregunta de fondo es: **¿qué define que dos destinos pertenecen al mismo mercado hotelero?**

**El problema de la fragmentación**: el dataset contiene ~26.000 nombres de ciudades distintos, con distribución de observaciones muy desigual. El trabajo en turismo hace que se consoliden datos de múltiples proveedores con sus propias estandarizaciones y criterios de nomenclatura. Esto lleva a tener registros que refieren a la misma ciudad bajo nombres distintos. La técnica desarrollada en el siguiente paso es una forma de homogeneizar la base de datos a nombres canónicos que permitan identificar los datos que corresponden a un mismo lugar. Es importante aplicar esta u otra estandarización equivalente para poder trabajar a una escala homogénea de análisis que permita comparaciones válidas. 

**El rol fundamental de `destination_with_nearest.csv`**: este archivo existe para atacar directamente ese problema. Para cada ciudad del dataset, asigna un `nearest_destination_id` — el ID de un destino canónico cercano que tenga masa suficiente de observaciones. Así, "Miami Beach", "South Beach" y "Brickell" dejan de ser tres mercados distintos con escasa historia y pasan a contribuir al mismo contexto de referencia. Sin esta consolidación, el análisis carece de la masa estadística necesaria para que cualquier comparación de precios sea confiable. Es la pieza que hace que el problema sea abordable con los datos disponibles.

**Por qué es una hipótesis y no una verdad**: el criterio de agrupación usado es proximidad geográfica — razonable, pero discutible. ¿Miami y Miami Beach comparten realmente la misma dinámica de precios, o tienen perfiles distintos que al mezclarlos se distorsionan mutuamente? ¿Es la cercanía geográfica el mejor indicador de mercado compartido, o lo son mejor la estacionalidad, el tipo de demanda, o el rango de precios? El ~40% de registros sin mapeo (que caen en fallback por ciudad) representa exactamente los destinos donde la evidencia histórica es más escasa y la comparación más incierta.

**El mercado va más allá de la geografía**: aunque la ubicación es la dimensión más intuitiva, un mercado hotelero comparable puede definirse igualmente por otras variables que produzcan grupos con comportamiento de precio homogéneo. La temporada del año, el día de la semana, la categoría del hotel o la duración de la estadía pueden ser tan determinantes como la geografía — o más. Quizás los precios de un destino de playa en julio se parecen más a los de otro destino de playa en julio que a los del mismo destino en enero: en ese caso la estación sería una dimensión de mercado más relevante que la geografía. La pregunta no es solo *dónde*, sino *cuándo*, *para qué tipo de viajero* y *bajo qué condiciones de oferta y demanda* dos precios son efectivamente comparables.

**Objetivo de esta pregunta**: ¿qué combinación de dimensiones produce grupos de observaciones donde la oferta y la demanda hotelera se mantienen suficientemente homogéneas como para que sus precios sean mutuamente informativos? Las dimensiones candidatas son: localización geográfica, día de la semana, mes o temporada, categoría de precio del hotel, duración de la estadía. No todas son igualmente relevantes — parte del trabajo del TP1 es determinar cuáles sí lo son y a qué escala.

*Variables a explorar: `city`, `state`, `country`, `destination_final`, `avg_price_average`, `count_repeated` (demanda), `avg_hotel_count` (oferta), `date_start` (para derivar DOW y estacionalidad), `nights` (duración de estadía), `number_of_adults`, `number_of_rooms`*

#### 2. Definición de contexto: ¿qué condiciones hacen que dos precios sean comparables?

El precio de un hotel nunca se evalúa en el vacío. Una habitación a $80/noche en Miami puede ser una ganga en diciembre (temporada alta) y un precio elevado en febrero (temporada baja). El mismo precio durante un evento masivo no es comparable con el precio en una semana sin eventos. Y una búsqueda para 1 adulto, 1 noche no es directamente comparable con una para 4 personas, 5 noches — aunque el precio total sea similar.

La pregunta es: **¿qué conjunto de variables define que dos búsquedas son suficientemente similares como para comparar sus precios?**

Dimensiones a considerar:
- **Temporal**: mes del año, semana del mes, día de la semana, días especiales o eventos
- **Composición del viaje**: noches de estadía, número de habitaciones, adultos, niños
- **Categoría del alojamiento**: ¿los hoteles más caros de un destino siguen sus propias dinámicas, independientes del mercado general?
- **Condiciones del mercado**: ¿el número de hoteles disponibles (`avg_hotel_count`) refleja la oferta y afecta los precios observados?

*La definición de CONTEXTO determina directamente la calidad de cualquier algoritmo de detección: un contexto mal definido produce comparaciones espurias aunque el método estadístico sea impecable.*

**Una precisión sobre la referencia de precio**: construir una referencia histórica no implica comparar precios de hoteles individuales. La referencia es una medida resumen del mercado — lo que el conjunto de opciones disponibles ofrece bajo condiciones comparables — no el precio de un alojamiento específico.

La función de la definición de mercado es, precisamente, *hacer comparables* los datos: identificar el subconjunto de observaciones que comparten condiciones suficientemente similares de oferta y demanda para que sus precios sean mutuamente informativos. Esta es la tarea central del TP2: definir esa granularidad. Una vez identificados los datos comparables y el nivel al que se agrupan, la elección del método de comparación se convierte en una decisión técnica con múltiples alternativas posibles.

#### 3. Algoritmo de detección: ¿cómo determinar si un precio es inusualmente bajo?

Una vez definidos el mercado (pregunta 1) y el contexto de comparación (pregunta 2), el problema se convierte en: **dado un precio observado y la distribución histórica del mercado para ese contexto, ¿cómo determinás si ese precio es inusualmente bajo?**

Hay múltiples enfoques posibles con distintos supuestos y trade-offs:
- **Estadísticos**: basados en la posición relativa del precio dentro de la distribución histórica (percentiles, distancia a la media o mediana, distribución empírica). Interpretables y eficientes, pero con supuestos implícitos sobre la forma de la distribución.
- **Supervisados**: si se pueden generar etiquetas de "oferta / no oferta" a partir de los datos históricos, es posible entrenar clasificadores. El desafío es definir qué constituye una etiqueta válida sin ground truth externo.
- **No supervisados**: clustering de patrones de precio por mercado — ¿emergen naturalmente grupos de contextos con comportamientos de precio cualitativamente distintos?

El repositorio documenta una exploración inicial hacia uno de estos enfoques. Esa exploración puede usarse como referencia de diseño, como punto de partida para entender el problema, o como baseline de comparación para una propuesta alternativa.

**Una pregunta abierta importante**: sin etiquetas externas de "esto era una oferta real", ¿cómo evaluás si tu algoritmo funciona bien o no? Diseñar métricas de evaluación significativas es parte del problema, no un paso posterior trivial.

---

### Dataset

Los archivos de datos son registros históricos de búsquedas de hoteles en la plataforma ID90Travel, agregados por combinación única de destino, fechas y composición de viaje.

#### Columnas principales

| Columna | Descripción | Ejemplo |
|---------|-------------|---------|
| `city`, `state`, `country`, `country_code` | Destino geográfico | `"Las Vegas"`, `"Nevada"`, `"United States"`, `"US"` |
| `date_start`, `date_end`, `nights` | Fechas y duración de la estadía | `2024-06-15`, `2024-06-18`, `3` |
| `number_of_rooms`, `number_of_adults`, `number_of_kids` | Composición del viaje | `1`, `2`, `0` |
| `count_repeated` | Cantidad de veces que se realizó esta búsqueda exacta — proxy de demanda | `127` |
| `avg_hotel_count` | Promedio de hoteles disponibles mostrados — proxy de oferta del mercado | `342` |
| `avg_price_average` | **Variable central**: precio promedio del conjunto de hoteles en USD | `186.50` |
| `max_price_high`, `min_price_low` | Rango de precios del mercado en esa búsqueda | `450.00`, `65.00` |

**Importante**: cada fila no representa el precio de un hotel individual, sino el rango estadístico de *todos* los hoteles mostrados en esa búsqueda.

#### Archivo de normalización de destinos: `destination_with_nearest.csv`

Este archivo mapea los ~26.000 nombres de ciudades distintos que aparecen en el dataset a un conjunto reducido de destinos canónicos. La lógica es simple: `"New York"`, `"New York City"` y `"NYC"` deben ser tratadas como el mismo mercado, no como tres mercados distintos con pocas observaciones cada uno.

El archivo asigna a cada ciudad un `nearest_destination_id` usando proximidad geográfica: si una ciudad no tiene un destino canónico asignado directamente, se le asigna el del destino más cercano en coordenadas.

**Esto es una hipótesis de agrupación, no una verdad absoluta.** Actualmente ~40% de los registros del dataset no tienen mapeo y usan el nombre de ciudad como identificador. Los estudiantes pueden cuestionar esta agrupación, explorar cómo afecta la calidad de los baselines y proponer agrupaciones alternativas.

---

### Hitos de la mentoría

Los tres primeros TPs tienen un hilo lógico: el TP1 construye el entendimiento del problema, el TP2 prepara los datos para resolverlo, y el TP3 lo resuelve. Cada grupo va a llegar a conclusiones distintas — eso es parte del punto.

#### TP1 — ¿Qué es un mercado en este problema? · Entrega 31/07

Antes de intentar detectar si un precio es una oferta, hay que resolver una pregunta más básica: *¿contra qué se compara ese precio?* La respuesta no es obvia. No alcanza con decir "contra otros precios del mismo destino" — porque los precios en Las Vegas un viernes de diciembre no tienen nada que ver con los de un martes de febrero, ni los de un hotel económico con los de uno de lujo.

El TP1 es una exploración abierta del dataset para entender qué dimensiones producen grupos de observaciones donde los precios se comportan de forma homogénea — es decir, donde comparar tiene sentido. Algunas dimensiones candidatas: la localización geográfica, el día de la semana, la temporada del año, la categoría del hotel, la duración de la estadía. No es necesario explorar todas — lo importante es llegar a una hipótesis razonada sobre qué combinación produce segmentos internamente coherentes y suficientemente densos como para sostener un análisis estadístico.

Vale preguntarse, por ejemplo: ¿los precios suben los fines de semana? ¿En todos los destinos por igual, o solo en los de ocio? ¿Los hoteles económicos siguen el mismo ciclo estacional que los de lujo? ¿Hay destinos donde la oferta disponible (`avg_hotel_count`) colapsa en ciertas fechas y eso afecta los precios de forma distinta al resto?

*Entrega: notebook con visualizaciones y una hipótesis documentada sobre qué segmentación de mercado propone usar el grupo — y por qué.*

#### TP2 — Preparar los datos y dar forma al mercado · Entrega 28/08

El TP2 tiene dos partes. La primera es operativa: limpiar y estructurar los datos para que sean comparables. Esto implica normalizar el precio a una unidad común (`precio_total / (noches × habitaciones × personas)`), construir las features de contexto que definen el mercado según lo que mostró el TP1 (día de la semana, mes, categoría de hotel, etc.), y aplicar el mapping de `destination_with_nearest.csv` para consolidar los ~26.000 nombres de ciudad en identificadores únicos — o proponer una agrupación alternativa con evidencia que la soporte. Es también el momento de auditar la calidad de los datos: precios inválidos, noches inconsistentes, búsquedas con ocupación cero.

La segunda parte es analítica: con los datos ya segmentados en mercados, explorar cómo se distribuyen los precios dentro de cada uno. ¿Qué forma tiene esa distribución? ¿Hay precios que claramente se alejan del resto? ¿Qué estadístico distingue mejor los precios inusualmente bajos — percentiles, distancia a la media, otra cosa? Este análisis no tiene que llegar a un algoritmo final, pero sí a primeras observaciones concretas que orienten el diseño del TP3.

La decisión más importante del TP2 es la definición de mercado que el grupo va a usar. Vale documentarla y justificarla con evidencia — porque condiciona todo lo que viene después.

*Entrega: dataset curado con features construidas, definición de mercado implementada, y análisis exploratorio de cómo se distribuyen los precios dentro de cada segmento.*

#### TP3 — El algoritmo · Entrega 25/09

Con los datos preparados y los mercados definidos, el TP3 es construir y evaluar un mecanismo que responda, para un precio dado en un contexto dado, si ese precio es inusualmente bajo.

El enfoque es libre: estadístico, supervisado, no supervisado, o una combinación. El repositorio documenta una exploración inicial que puede servir como referencia o punto de partida, no como destino obligado. Lo que importa no es la sofisticación del método sino poder argumentar por qué tiene sentido para este problema, qué supuestos implica y qué limitaciones tiene.

Una pregunta que conviene anticipar desde el principio: sin etiquetas externas de "esto era una oferta real", ¿cómo se evalúa si el algoritmo funciona bien? Diseñar métricas de evaluación que tengan sentido es parte del trabajo, no un detalle a resolver al final. Y una vez que el algoritmo esté implementado, vale probar qué tan sensible es a la definición de mercado del TP2 — un cambio en la segmentación puede cambiar significativamente qué precios se clasifican como oferta.

*Entrega: implementación del algoritmo, evaluación de resultados, análisis de sensibilidad a la segmentación del TP2, y conclusiones honestas sobre qué funciona y qué no.*

#### TP4 — Video de presentación final · Entrega 26/10

Presentación en video del proyecto completo. Las jornadas finales son el **4 y 5 de diciembre**.

---

### Referencia: scripts de extracción de datos

Los archivos `query_historicos.py` y `data/query_historicos_*.py` contienen las consultas SQL que se usaron para extraer los datos históricos desde la base de datos PostgreSQL interna de ID90Travel. **No es necesario ejecutarlos** — los datos ya están disponibles en Drive. Sin embargo, son útiles como referencia si quieren entender exactamente qué tabla y qué campos se consultaron, o si en algún TP deciden proponer una consulta alternativa (por ejemplo, para cruzar con datos de reservas o agregar a diferente granularidad).

---

## 1. Contexto: ID90Travel y el Problema

### Quiénes son los usuarios

ID90Travel es una plataforma de viajes corporativos que ofrece tarifas preferenciales a empleados activos de aerolíneas y sus beneficiarios. El catálogo incluye hoteles, vuelos y otros productos de viaje. Los usuarios — tripulantes de cabina, pilotos, personal de tierra — están habituados a moverse con criterio de costo, pero no tienen una referencia objetiva para evaluar si el precio de un hotel en un destino puntual representa una oportunidad real o no.

### El problema concreto

El precio de un hotel varía significativamente según el destino, la temporada, la semana del mes, la anticipación de la búsqueda y la composición del viaje. Una habitación en Las Vegas en diciembre puede costar $80 en una semana y $300 en la siguiente. Un usuario que no conoce ese destino no puede distinguir cuál es el precio normal de mercado y cuál es la excepción.

La plataforma no cuenta actualmente con una señal que ayude al usuario a tomar esa decisión. El resultado es que oportunidades reales de precio pasan desapercibidas, y precios normales generan la percepción errónea de que el producto es caro.

### Lo que se propone

Este proyecto propone una primera solución al problema usando análisis estadístico histórico: si se cuenta con suficientes búsquedas pasadas para un destino y período dado, es posible construir una distribución de precios de referencia y comparar cualquier precio nuevo contra esa distribución. El resultado de esa comparación es la etiqueta que se mostraría al usuario durante la búsqueda.

**Esta propuesta es tentativa y exploratoria.** Se diseñó como exploración de ciclo rápido usando los datos históricos más accesibles disponibles en la plataforma. A lo largo del documento se identifican sus limitaciones y se describen los caminos para evolucionar la solución.

---

## 2. Objetivo del Proyecto

Cuando un usuario busca un hotel en ID90Travel, ve una lista de resultados con precios. El objetivo de este proyecto es clasificar ese precio automáticamente y mostrar una etiqueta de contexto junto al resultado:

> **¿El precio que se le muestra al usuario en este momento, para este destino y estas fechas, es una oferta o no?**

La clasificación se realiza en una escala de cinco categorías: *Deal, Good Price, Normal Price, Expensive, Very Expensive*. Esta etiqueta permite al usuario tomar una decisión informada sin necesitar conocimiento previo del mercado.

**Un aspecto clave del enfoque**: lo que constituye una oferta no es absoluto ni universal. Un precio de $80 por noche puede ser una oportunidad en Las Vegas y completamente normal en un destino más económico. La clasificación es siempre relativa a la distribución histórica de precios del propio destino consultado: el sistema aprende qué es "barato" o "caro" para cada mercado de forma independiente. Esto es especialmente relevante en una plataforma global donde coexisten destinos con perfiles de precio muy distintos.

---

## 3. Flujo de Trabajo: Scripts y Resultados

El sistema se construye en tres etapas secuenciales. La primera requiere acceso a la base de datos interna; las dos siguientes operan sobre archivos CSV locales.

```
┌─────────────────────────────────────────────────────────┐
│  ETAPA 1 — Extracción de datos históricos               │
│  Script: query_historicos.py                            │
│  Entrada: Base de datos PostgreSQL (acceso interno)     │
│  Salida:  data/datos_historicos_YYYY.csv (~200 MB/año)  │
│           Un archivo por año. Contiene ~2.5M registros  │
│           de búsquedas hoteleras agregadas.             │
└─────────────────────────────┬───────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│  ETAPA 2 — Procesamiento y generación de líneas de base │
│  Script: pipeline_build_baselines.py                    │
│  Entrada: data/datos_historicos_*.csv                   │
│  Salida:  outputs/market_baselines.csv  (52 MB)         │
│           outputs/price_distribution.csv (3 MB)         │
│           outputs/bucket_summary.csv                    │
│  Duración: ~2.5 minutos sobre 10.7M observaciones       │
└─────────────────────────────┬───────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│  ETAPA 3 — Aplicación web de clasificación              │
│  Script: streamlit run app.py                           │
│  Entrada: Los tres archivos de outputs/                 │
│  Salida:  Interfaz web en localhost:8501                │
│           El usuario ingresa una búsqueda y recibe      │
│           la clasificación de precio en tiempo real.    │
└─────────────────────────────────────────────────────────┘
```

### Cuándo ejecutar cada script

**`query_historicos.py`** — se ejecuta para obtener o actualizar los datos históricos. Requiere acceso a la base de datos interna. Si los datos ya están disponibles de forma externa (ver sección [Cómo Ejecutar](#14-cómo-ejecutar-el-proyecto)), esta etapa puede omitirse. Acepta el año como argumento:

```bash
python query_historicos.py 2024   # extrae datos del año 2024
python query_historicos.py 2025   # extrae datos del año 2025
```

**`pipeline_build_baselines.py`** — se ejecuta una vez después de obtener o actualizar los datos históricos, para regenerar las líneas de base. Debe volver a ejecutarse cada vez que se incorporen datos de un nuevo año o se modifiquen los parámetros del sistema en `config.py`.

**`app.py`** — se ejecuta cada vez que se quiere usar la interfaz. Carga los archivos de `outputs/` al iniciar y queda disponible en el navegador hasta que se detiene el proceso.

---

## 4. Contenido del Repositorio

| Archivo | Propósito | Por qué es importante |
|---------|-----------|----------------------|
| `query_historicos.py` | Extrae datos de búsquedas históricas desde PostgreSQL | Define exactamente qué datos se usaron y de qué tabla provienen |
| `pipeline_build_baselines.py` | Orquesta el procesamiento en 11 pasos para generar las líneas de base | Es el flujo completo desde datos crudos hasta los archivos que consume la aplicación |
| `auxiliary_functions.py` | Implementa todas las funciones de procesamiento y clasificación | Contiene el núcleo del sistema: normalización de precios, cálculo de percentiles, z-scores y clasificación |
| `config.py` | Configuración centralizada del sistema | Define todos los parámetros clave: umbrales de clasificación, percentiles de segmentación, reglas de validación |
| `app.py` | Interfaz web Streamlit para clasificación interactiva | Muestra cómo se integra el sistema al flujo de búsqueda de un usuario real |
| `test_system.py` | Tests unitarios de las funciones principales | Verifica la correctitud de la normalización de precios y la lógica de clasificación |
| `exploratory_analysis.ipynb` | Notebook de ejemplo del flujo de procesamiento con datos reales | Carga los datasets desde `data/`, recorre las etapas del pipeline paso a paso y muestra cómo clasificar un precio — punto de partida recomendado para el TP1 |
| `data/destination_with_nearest.csv` | Mapping de ciudades a destinos canónicos | Normaliza los ~26.000 nombres de ciudades del dataset en identificadores únicos de destino |
| `data/query_historicos_2024.py` | Script standalone de extracción para el año 2024 | Documenta la query original usada para obtener los datos históricos |

**Archivos de datos no incluidos** (`data/datos_historicos_*.csv`, `outputs/`): superan el límite de tamaño de GitHub. Se distribuyen por separado; ver sección [Cómo Ejecutar el Proyecto](#14-cómo-ejecutar-el-proyecto).

---

## 5. Fuentes de Datos Disponibles

### Qué datos se necesitan

Para clasificar si un precio es una oferta, el sistema necesita una referencia histórica del mercado: *¿qué precios se han ofrecido típicamente para este destino, en este período, para esta composición de viaje?* Esa referencia debe capturar la distribución completa de precios disponibles en el mercado, no únicamente los precios que alguien decidió reservar.

En ID90Travel existen tres familias de datos posibles para construir esa referencia, con distintos niveles de granularidad, sesgo y cobertura.

---

### Familia 1 — `analytic.customer_shopping_model` (datos de búsqueda)

Esta tabla registra los eventos de búsqueda que los usuarios realizan en la plataforma. Según el tipo de interacción del usuario, se generan registros con distinta granularidad.

#### Tipo `HOTELS` — **fuente utilizada en la exploración inicial**

Se genera una vez por cada búsqueda general: cuando el usuario ingresa un destino y fechas y el sistema devuelve la lista de hoteles disponibles. El registro captura el **resumen estadístico de todos los precios mostrados** en esa pantalla de resultados.

| Columna en el dataset | Descripción |
|-----------------------|-------------|
| `city`, `state`, `country`, `country_code` | Identificación geográfica del destino buscado |
| `date_start`, `date_end`, `nights` | Fechas de check-in, check-out y duración de la estadía |
| `number_of_adults`, `number_of_rooms`, `number_of_kids` | Composición de la búsqueda |
| `avg_hotel_count` | Promedio de hoteles disponibles mostrados (indicador de oferta del mercado) |
| `min_hotel_count`, `max_hotel_count` | Rango de disponibilidad de hoteles en las búsquedas agrupadas |
| `avg_price_average` | Precio promedio del conjunto de hoteles mostrados en la búsqueda |
| `max_price_high` | Precio más alto mostrado |
| `min_price_low` | Precio más bajo mostrado |
| `count_repeated` | Cantidad de veces que se realizó esta búsqueda exacta (proxy de demanda) |

**Limitación clave de esta fuente**: el registro no contiene el precio de un hotel individual. Únicamente captura el rango estadístico del conjunto de hoteles mostrados. No es posible saber qué precio vio el usuario para una propiedad específica.

#### Tipos `ROOM`, `ROOMS`, `RATES` — alternativa de mayor granularidad

Se generan cuando el usuario hace clic en un hotel y navega sus habitaciones disponibles. Cada registro representa el precio de una habitación puntual en un hotel específico, incluyendo el precio exacto mostrado en pantalla.

| Columna adicional | Descripción |
|-------------------|-------------|
| `hotel_id`, `hotel_name`, `star_ratings` | Identificación del hotel específico |
| `room_type`, `display_rate` | Tipo de habitación y precio exacto mostrado al usuario |
| `display_rate_with_promo`, `total_discount_amount` | Precio con descuento si aplica |
| `retail_rate` | Tarifa retail de referencia |
| `subtotal`, `taxes_and_fees`, `total` | Desglose completo del precio final |
| `latitude`, `longitude` | Coordenadas del hotel |
| `member_id`, `trace_id`, `log_timestamp` | Identificación de sesión del usuario |

Esta fuente habilitaría un análisis a nivel de hotel individual, mucho más preciso que el actual, pero con un volumen de datos considerablemente mayor.

---

### Familia 2 — `public.hotel_booking` (datos transaccionales)

Esta tabla registra únicamente las transacciones que terminaron en una reserva efectiva. Es la única fuente que contiene información económica real: el costo que pagó la plataforma al proveedor y el margen resultante.

| Columna | Descripción |
|---------|-------------|
| `markup_base_rate` | Costo real del proveedor (COGS) |
| `net_revenue` | Ingreso neto de la transacción |
| `li_dtl_tot_amt` | Valor bruto de la reserva (GBV) |
| `markup_percent` | Margen aplicado sobre COGS |
| `vendor_name` | Proveedor de la tarifa (Expedia, HotelBeds, etc.) |
| `booking_window` | Días de anticipación entre la reserva y la estadía |
| `cancelled` | Indica si la reserva fue cancelada |

**Por qué no es la fuente primaria en la exploración inicial**: introduce sesgo de selección. Solo captura los precios que alguien aceptó pagar, omitiendo los precios altos que el mercado mostró pero nadie reservó. Usar datos de booking como referencia histórica subestimaría sistemáticamente qué tan buena es una oferta, porque la distribución de referencia ya estaría filtrada hacia precios que los usuarios encontraron razonables.

---

### Comparativa y decisión

| Dimensión | HOTELS shopping (actual) | ROOM/RATES shopping | hotel_booking |
|-----------|--------------------------|---------------------|---------------|
| Precio individual por hotel | ❌ Solo rangos | ✅ Precio exacto | Implícito via COGS |
| Sesgo de selección | Ninguno | Ninguno | Solo precios aceptados |
| Volumen de datos | Medio | Alto | Bajo |
| Información económica | ❌ | ❌ | ✅ COGS, margen, NR |
| Granularidad del análisis | Destino + período | Hotel + habitación | Transacción confirmada |

### Posibles evoluciones del análisis

| Nivel | Fuente | Pregunta que permite responder |
|-------|--------|-------------------------------|
| **Exploración inicial** | `HOTELS` shopping | ¿Está el rango de precios de este destino/fecha por debajo del histórico? |
| Nivel 2 | `ROOM/RATES` shopping | ¿Está este hotel específico ofreciendo un precio inusualmente bajo hoy? |
| Nivel 3 | Shopping + booking | ¿Es esta oferta barata para el mercado y también rentable para la plataforma? |

---

## 6. Enfoque Explorado: Aproximación Estadística

> *Lo que sigue documenta una de las aproximaciones al problema exploradas en este proyecto. Se presenta como referencia de diseño, no como la solución correcta. Los supuestos tomados, los umbrales elegidos y las decisiones de agrupación son discutibles y pueden mejorarse.*

### Descripción del enfoque

El enfoque explorado es un **clasificador estadístico** que no requiere entrenamiento supervisado ni etiquetado manual de datos. En lugar de aprender de ejemplos de "oferta vs. no oferta", construye distribuciones de referencia a partir del historial de búsquedas y clasifica cada nuevo precio según su posición relativa en esa distribución. Este enfoque es interpretable y puede actualizarse simplemente re-ejecutando el pipeline sobre datos más recientes.

### Qué es una línea de base (*baseline*)

Una **línea de base** es la distribución estadística histórica del precio normalizado para un contexto específico de búsqueda. Un contexto queda definido por cuatro dimensiones:

```
contexto = destino × mes × semana del mes × segmento de precio
```

Por ejemplo: *Las Vegas + diciembre + semana 3 + segmento medio*. Para ese contexto, la línea de base contiene la media, desviación estándar, mínimo, máximo y cantidad de observaciones históricas acumuladas. El sistema tiene 635.022 líneas de base, una por cada combinación que ocurrió en los datos históricos con suficiente frecuencia.

### El problema de comparar búsquedas heterogéneas

El primer desafío técnico es que las búsquedas no son directamente comparables. Una estadía de 7 noches con 2 habitaciones y 4 personas tiene un precio total muy distinto a una de 1 noche con 1 habitación y 1 persona, aunque el precio unitario sea el mismo. Comparar precios totales llevaría a conclusiones incorrectas.

**Solución**: normalizar el precio a una unidad común antes de cualquier comparación.

```
precio_normalizado = precio_total / (noches × habitaciones × (adultos + niños))
```

Esto produce un **precio por persona, por habitación, por noche** directamente comparable entre búsquedas de cualquier composición.

### El problema de comparar categorías distintas de hotel

El segundo desafío es que hoteles de distintas categorías de precio no deben compararse entre sí. Un hotel de lujo a $200/noche siempre parecerá caro si se compara contra un histórico que incluye alojamientos a $30. El z-score resultante sería alto aunque el precio sea perfectamente normal para su categoría.

**Solución**: segmentar las búsquedas en tres categorías de precio (*segmentos*) antes de comparar, usando los percentiles históricos del propio destino como umbrales. Cada búsqueda se compara únicamente contra el histórico de su mismo segmento.

| Segmento | Umbral | Etiqueta |
|----------|--------|----------|
| `low` | precio_normalizado ≤ percentil 25 del destino | Budget |
| `medium` | entre percentil 25 y 75 | Mid-Range |
| `high` | precio_normalizado ≥ percentil 75 | Premium |

Los percentiles se calculan de forma independiente para cada destino, lo que garantiza que los umbrales reflejen la estructura de precios local y no una referencia global.

### El índice de clasificación: z-score contextual

Una vez que se tiene el precio normalizado y se conoce el segmento del hotel, el sistema busca la línea de base correspondiente (destino + mes + semana del mes + segmento) y calcula el **z-score**:

```
z = (precio_normalizado − media_histórica) / desviación_estándar_histórica
```

El z-score mide cuántas desviaciones estándar está el precio actual respecto al promedio histórico de búsquedas comparables. Un valor negativo indica que el precio está por debajo del promedio; cuanto más negativo, más significativa es la oportunidad.

### Clasificación final

| Clasificación | Rango z-score | Interpretación para el usuario |
|--------------|---------------|-------------------------------|
| **Deal** | z < −1.0 | Precio significativamente por debajo del histórico |
| **Good Price** | −1.0 ≤ z < −0.5 | Precio por debajo del promedio del mercado |
| **Normal Price** | −0.5 ≤ z ≤ 0.5 | Precio dentro del rango esperado |
| **Expensive** | 0.5 < z < 1.0 | Precio por encima del promedio |
| **Very Expensive** | z ≥ 1.0 | Precio significativamente elevado |
| **Insufficient Data** | — | No hay suficiente historial para este contexto |

### Índice complementario: Relative Price Index

```
relative_price_index = precio_normalizado / mediana_histórica_del_destino
```

Métrica de interpretación intuitiva que no depende de la desviación estándar. Un valor de `0.70` indica que el precio actual es un 30% más barato que la mediana histórica del destino, independientemente del segmento. Se presenta como información complementaria junto al z-score.

### Ejemplo completo de clasificación

A continuación se ilustra el flujo de clasificación para una búsqueda concreta:

> **Búsqueda**: Las Vegas · 16–19 de diciembre · 2 adultos · 1 habitación · precio total $450

**Paso 1 — Normalización**
```
precio_normalizado = $450 / (3 noches × 1 hab × 2 adultos) = $75 por persona-hab-noche
```

**Paso 2 — Determinación del segmento**

Se consulta `price_distribution.csv` para Las Vegas:
- p25 = $45 · p50 = $62 · p75 = $85

Como $75 está entre p25 y p75 → **segmento: medium (Mid-Range)**

**Paso 3 — Búsqueda de la línea de base**

Se consulta `market_baselines.csv` para el contexto:
```
destino: Las Vegas · mes: 12 · semana: 3 · segmento: medium
→ media = $68 · desv. estándar = $15 · observaciones = 342
```

**Paso 4 — Cálculo del z-score**
```
z = ($75 − $68) / $15 = 0.47
```

**Resultado**: z = 0.47 → **Normal Price** ✓

El precio es ligeramente superior al promedio histórico pero dentro del rango esperado para la tercera semana de diciembre en ese segmento.

### Flujo de clasificación en tiempo real (runtime)

Cuando el usuario usa la aplicación, el sistema ejecuta los pasos anteriores en milisegundos:

```
Usuario ingresa búsqueda (destino, fechas, ocupación, precio)
         ↓
Normalizar precio → precio_normalizado
         ↓
Consultar price_distribution.csv → determinar segmento (low/medium/high)
         ↓
Consultar market_baselines.csv → obtener media y desv. estándar del contexto
         ↓  [si no existe baseline para ese segmento → fallback a baseline general]
Calcular z-score
         ↓
Aplicar umbrales → clasificación (Deal / Good Price / Normal / Expensive / Very Expensive)
         ↓
Mostrar etiqueta + nivel de confianza + Relative Price Index
```

### La aplicación web (`app.py`)

La interfaz Streamlit permite clasificar cualquier búsqueda sin escribir código. El usuario selecciona el destino desde un menú desplegable, ingresa las fechas, la composición del viaje y el precio total observado. El sistema responde con:

- **Banner de clasificación** con color según resultado (verde para Deal, rojo para Very Expensive)
- **Z-score y nivel de confianza** (High / Medium / Low según observaciones históricas del contexto)
- **Segmento del hotel** (Budget / Mid-Range / Premium) con sus umbrales p25 y p75
- **Relative Price Index** y percentiles del destino (p25, p50, p75)
- **Estadísticas de la línea de base**: media, desviación estándar, cantidad de observaciones

---

## 7. Query de Extracción de Datos

El script [`query_historicos.py`](query_historicos.py) extrae los datos desde PostgreSQL. Las credenciales de conexión se configuran mediante variables de entorno (ver [`config.py`](config.py)). El año a extraer se pasa como argumento al ejecutar el script.

### SQL

```sql
SELECT 
    h.city,
    h.state,
    h.country,
    h.country_code,
    a.date_start,
    a.date_end,
    a.number_of_adults,
    a.number_of_rooms,
    a.number_of_kids,
    a.nights,
    COUNT(*)                  AS count_repeated,
    AVG(a.hotel_count)        AS avg_hotel_count,
    MIN(a.hotel_count)        AS min_hotel_count,
    MAX(a.hotel_count)        AS max_hotel_count,
    AVG(a.price_average)      AS avg_price_average,
    MAX(a.price_high)         AS max_price_high,
    MIN(a.price_low)          AS min_price_low
FROM
    analytic.customer_shopping_model AS a
JOIN
    analytic.hotel_city_location AS h ON a.hotel_id = h.hotel_id
WHERE
    a.date_start >= '{year}-01-01'
    AND a.date_start < '{year + 1}-01-01'
    AND a.date_end   >= '{year}-01-01'
    AND a.date_end   < '{year + 1}-01-01'
    AND a.type = 'HOTELS'
GROUP BY
    h.city, a.date_start, a.date_end,
    a.number_of_adults, a.number_of_kids, a.number_of_rooms, a.nights,
    h.state, h.country, h.country_code;
```

### Decisiones de diseño de la query

**`JOIN analytic.hotel_city_location`**: La tabla de shopping almacena `hotel_id` pero no la geografía del hotel. El join trae ciudad, estado, país y código de país desde la tabla maestra de hoteles, lo que permite agrupar búsquedas por destino geográfico.

**`WHERE a.type = 'HOTELS'`**: Filtra exclusivamente los eventos de búsqueda general, descartando los eventos de tipo `ROOM`, `ROOMS` y `RATES`. Como se explicó en la sección de fuentes, esta decisión limita el análisis a rangos de precio del mercado en lugar de precios por hotel individual.

**`GROUP BY` sobre parámetros de búsqueda**: El mismo contexto de búsqueda puede ser realizado por cientos de usuarios distintos en un mismo día, generando múltiples filas idénticas en la tabla origen. El `GROUP BY` consolida todos esos eventos en un único registro estadístico, capturando el rango de precios del mercado para esa combinación exacta de destino, fechas y ocupación.

**`COUNT(*) AS count_repeated`**: La cantidad de eventos agrupados actúa como proxy de demanda. Un valor de 500 para un destino y semana particular indica que 500 usuarios realizaron exactamente esa búsqueda — señal de alta demanda en ese período. Esta variable se usa más adelante para ponderar las medias históricas.

**`AVG/MIN/MAX` sobre hotel_count y precios**: Como el `GROUP BY` colapsa múltiples eventos, las métricas de disponibilidad y precio se capturan con tres estadísticos que representan el rango del mercado durante el período analizado.

---

## 8. Dataset: Descripción del Esquema de Datos

El archivo resultante de la query es `data/datos_historicos_YYYY.csv`. Para el año 2024 contiene aproximadamente **2.5 millones de registros** y pesa ~200 MB. Cada fila representa una combinación única de parámetros de búsqueda con sus estadísticas de mercado agregadas.

### Columnas originales (producidas por la query)

| Columna | Tipo | Descripción | Ejemplo |
|---------|------|-------------|---------|
| `city` | string | Ciudad del hotel buscado | `"Las Vegas"` |
| `state` | string | Estado o provincia | `"Nevada"` |
| `country` | string | País del hotel | `"United States"` |
| `country_code` | string | Código de país ISO 3166-1 de 2 letras | `"US"` |
| `date_start` | date | Fecha de check-in buscada | `2024-06-15` |
| `date_end` | date | Fecha de check-out buscada | `2024-06-18` |
| `nights` | int | Duración de la estadía según la BD | `3` |
| `number_of_rooms` | int | Habitaciones solicitadas | `1` |
| `number_of_adults` | int | Adultos incluidos en la búsqueda | `2` |
| `number_of_kids` | int | Niños incluidos (puede ser 0) | `0` |
| `count_repeated` | int | Veces que se realizó esta búsqueda exacta | `127` |
| `avg_hotel_count` | float | Promedio de hoteles disponibles mostrados | `342.5` |
| `min_hotel_count` | int | Mínimo de hoteles disponibles en las búsquedas agrupadas | `280` |
| `max_hotel_count` | int | Máximo de hoteles disponibles | `410` |
| `avg_price_average` | float | Precio promedio del mercado en USD | `186.50` |
| `max_price_high` | float | Precio más alto del mercado mostrado (USD) | `450.00` |
| `min_price_low` | float | Precio más bajo del mercado mostrado (USD) | `65.00` |

### Columnas derivadas (añadidas por el pipeline)

El pipeline agrega las siguientes columnas al dataset durante el procesamiento. No están en el archivo CSV original.

| Columna | Agregada en | Descripción |
|---------|-------------|-------------|
| `avg_price_average_std` | Paso 3 | Precio normalizado: `avg_price_average / (nights × rooms × (adults + kids))` |
| `date` | Paso 4 | Fecha individual de cada noche de la estadía (expansión temporal) |
| `month` | Paso 5 | Mes del año (1–12) derivado de `date` |
| `week_in_month` | Paso 5 | Semana del mes (1–4) según rangos fijos |
| `destination_final` | Paso 6 | ID del destino canónico tras aplicar el mapping |
| `destination_name` | Paso 6 | Nombre legible del destino canónico |
| `price_bucket` | Paso 8 | Segmento de precio: `"low"`, `"medium"` o `"high"` |

**Nota sobre `avg_price_average`**: es la variable de análisis central. No representa el precio de un hotel individual sino el precio promedio de todos los hoteles listados en ese resultado de búsqueda. El sistema construye sus distribuciones históricas sobre este valor.

**Nota sobre `nights`**: proviene directamente de la base de datos; en general coincide con `date_end - date_start`, pero no está validado de forma exhaustiva en el pipeline.

---

## 9. Archivo de Normalización de Destinos

**Archivo**: `data/destination_with_nearest.csv` (1.2 MB, 15.989 referencias)

### Por qué existe este archivo y por qué es fundamental

El dataset contiene ~26.000 nombres de ciudades distintos — muchos de ellos variantes de la misma ciudad (`"New York"`, `"New York City"`, `"NYC"`) o ciudades satélite de un mismo mercado (`"Miami Beach"`, `"South Beach"`, `"Brickell"`). Si cada nombre de ciudad se trata como un mercado independiente, la mayoría tiene tan pocas observaciones históricas que resulta imposible construir distribuciones de precio estadísticamente confiables sobre ellas.

Este archivo resuelve ese problema mapeando cada ciudad a un **destino canónico** con un ID numérico único. El mecanismo es simple: para cada ciudad del dataset, se asigna el `nearest_destination_id` del destino con mayor masa de datos que esté geográficamente más cerca. Así, observaciones de decenas de ciudades cercanas se consolidan en un único contexto de referencia con cientos o miles de registros — lo que hace posible cualquier análisis estadístico posterior.

**Es la pieza que hace abordable el problema**: sin esta consolidación, la gran mayoría de los ~26.000 "mercados" carecen de suficiente historia para cualquier comparación de precios significativa. El archivo transforma un problema de datos fragmentados en un conjunto de ~50–100 mercados con masa crítica.

**Sin embargo, es una hipótesis**: el criterio de agrupación (proximidad geográfica) es razonable pero discutible. "Más cercano geográficamente" no equivale a "mismo mercado hotelero". Destinos cercanos pueden tener perfiles de precio estructuralmente distintos si sirven a tipos de viajeros diferentes. Esta hipótesis conecta directamente con la primera pregunta de investigación de la mentoría.

### Columnas

| Columna | Descripción | Ejemplo |
|---------|-------------|---------|
| `reference` | Clave de lookup: `country_code - state_code - city` | `"US - NV - Las Vegas"` |
| `city` | Nombre de ciudad tal como aparece en el dataset | `"Las Vegas"` |
| `latitude` | Latitud geográfica del centroide de la ciudad | `36.174465` |
| `longitude` | Longitud geográfica | `-115.137389` |
| `nearest_destination_id` | ID numérico del destino canónico asignado | `50643` |
| `nearest_destination_name` | Nombre legible del destino canónico | `"Las Vegas"` |

El `nearest_destination_id` es la clave que usa el sistema en todos los pasos posteriores: cálculo de percentiles, construcción de líneas de base y evaluación en la aplicación. En caso de que una ciudad no tenga mapeo canónico (ocurre en ~40% de los destinos del dataset), el sistema usa el nombre de ciudad como identificador de fallback — esos destinos tienen distribuciones históricas más pobres y cualquier análisis sobre ellos es menos confiable.

La cobertura del mapping no es homogénea: los mercados más grandes y más buscados (ciudades norteamericanas principales) están bien cubiertos; destinos internacionales o ciudades pequeñas tienden a quedar sin mapeo. Entender este sesgo de cobertura es parte del trabajo del TP2.

---

## 10. Pipeline de Procesamiento

El script [`pipeline_build_baselines.py`](pipeline_build_baselines.py) coordina el procesamiento en 12 pasos secuenciales. Las funciones que implementan cada paso se encuentran en [`auxiliary_functions.py`](auxiliary_functions.py). El proceso completo toma aproximadamente 2.5 minutos sobre 10.7 millones de observaciones.

```
data/datos_historicos_*.csv
           ↓
      [11 pasos]
           ↓
outputs/market_baselines.csv    ← 635.022 líneas de base
outputs/price_distribution.csv  ← percentiles por destino
outputs/bucket_summary.csv      ← reporte de cobertura
```

### Paso 1 — Cargar datos históricos

Carga todos los archivos `datos_historicos_*.csv` del directorio `data/` y los concatena en un único DataFrame. Soporta múltiples años de datos.

### Paso 2 — Eliminar duplicados

Elimina filas completamente idénticas que pueden aparecer cuando se procesan archivos de distintas extracciones.

### Paso 3 — Validar datos

Filtra los registros que harían inválida la fórmula de normalización: aquellos donde `nights ≤ 0`, `rooms ≤ 0`, o `(adults + kids) ≤ 0`. En la práctica afecta a una proporción mínima de los datos, pero su presencia causaría divisiones por cero o valores normalizados sin sentido. Este paso se agregó como control de calidad una vez detectados registros inválidos en los datos de origen.

### Paso 4 — Normalizar precios

Aplica la fórmula de normalización a cada registro de forma vectorizada. El resultado se almacena en la columna `avg_price_average_std`.

**Nota sobre la evolución de la fórmula**: versiones anteriores del sistema usaban una fórmula aditiva (`precio / (nights + rooms + adults + kids)`), que producía resultados sesgados para búsquedas con familias numerosas o estadías largas. La versión actual usa el producto, que escala correctamente con todos los parámetros.

### Paso 5 — Expandir fechas

Cada registro representa una estadía que abarca múltiples noches. Para construir distribuciones de precio con resolución semanal (semana del mes), es necesario que cada noche de esa estadía aparezca como una observación independiente.

Este paso transforma cada registro de estadía en N registros diarios, donde N = número de noches. El dataset pasa de ~2.5 millones de registros a ~10.7 millones de observaciones diarias.

Implementado con `numpy.repeat` en lugar de iteración fila a fila, lo que reduce el tiempo de ejecución de este paso en aproximadamente 1000x.

### Paso 6 — Generar features temporales

Agrega dos columnas a cada observación diaria:
- `month`: mes del año (1–12)
- `week_in_month`: semana del mes (1–4) según rangos fijos: días 1–7, 8–15, 16–22, 23–31

Estas dos features son los ejes de la segmentación temporal: el mercado hotelero de Las Vegas en la tercera semana de diciembre (pre-Navidad) tiene un perfil de precios distinto al de la segunda semana del mismo mes.

### Paso 7 — Mapear destinos

Aplica el archivo `destination_with_nearest.csv` para asignar a cada registro un `destination_id` canónico. El merge se realiza por la clave compuesta `country_code - state_code - city` usando índices de pandas para optimizar la velocidad.

### Paso 8 — Calcular distribución de precios por destino

Para cada destino, calcula los percentiles `p10`, `p25`, `p50`, `p75` y `p90` sobre todas sus observaciones históricas de precio normalizado. Los percentiles `p25` y `p75` son los umbrales que definen los límites de cada segmento en el paso siguiente. El resultado se guarda en `outputs/price_distribution.csv`.

### Paso 9 — Clasificar observaciones en segmentos

Usando los percentiles del paso anterior, asigna a cada observación una etiqueta de segmento (`low`, `medium`, `high`). Esta clasificación define la "categoría de mercado" a la que pertenece esa búsqueda y determina contra qué distribución histórica se comparará.

### Paso 10 — Calcular líneas de base

Para cada combinación única de `[destination_id, month, week_in_month, price_bucket]`, calcula:
- `mean_price_std`: **media ponderada** por `count_repeated` — las búsquedas más frecuentes reciben mayor peso porque representan condiciones de mercado más típicas; un contexto buscado 500 veces en las mismas condiciones es más representativo que uno buscado solo 2 veces
- `std_price_std`: desviación estándar
- `min_price_std`, `max_price_std`: rango observado
- `count_obs`: número de observaciones diarias en ese contexto

El resultado es la tabla de 635.022 líneas de base en `outputs/market_baselines.csv`.

### Paso 11 — Validaciones de robustez

Agrega una columna `low_confidence = True` a contextos con menos de 30 observaciones. También aplica una desviación estándar mínima dinámica: `std = max(std, media × 0.10)`, para evitar z-scores sin sentido en contextos donde todos los precios históricos son idénticos.

### Paso 12 — Guardar resultados

Escribe los tres archivos de output en `outputs/` y registra estadísticas finales: total de contextos, distribución por segmento, porcentaje de contextos con alta confianza.

---

## 11. Datasets Generados (Outputs)

En ID90Travel, la aplicación carga estos archivos al inicializarse para poder responder consultas de clasificación en tiempo real. Son el producto final del pipeline y la interfaz entre el procesamiento histórico y la experiencia del usuario.

No se incluyen en el repositorio porque superan los límites de tamaño de GitHub y se regeneran íntegramente en aproximadamente 2.5 minutos ejecutando `pipeline_build_baselines.py` sobre el dataset histórico.

### `outputs/market_baselines.csv` — 52 MB, 635.022 filas

La tabla principal del sistema. Cada fila es la distribución estadística histórica de un contexto específico de búsqueda.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `destination_final` | string/int | ID del destino canónico |
| `destination_name` | string | Nombre legible del destino |
| `month` | int | Mes (1–12) |
| `week_in_month` | int | Semana del mes (1–4) |
| `price_bucket` | string | Segmento: `"low"`, `"medium"`, `"high"` |
| `mean_price_std` | float | Media ponderada del precio normalizado histórico |
| `std_price_std` | float | Desviación estándar histórica |
| `min_price_std` | float | Precio mínimo observado en este contexto |
| `max_price_std` | float | Precio máximo observado |
| `count_obs` | int | Observaciones diarias acumuladas en este contexto |
| `low_confidence` | bool | `True` si `count_obs < 30` |

### `outputs/price_distribution.csv` — 3 MB, 26.684 filas

Percentiles de precio normalizado por destino. Usado en tiempo de ejecución para determinar en qué segmento cae una nueva búsqueda antes de buscar su línea de base.

| Columna | Descripción |
|---------|-------------|
| `destination_final` | ID del destino |
| `destination_name` | Nombre del destino |
| `n_observations` | Total de observaciones históricas del destino |
| `p10`, `p25`, `p50`, `p75`, `p90` | Percentiles de la distribución de precios normalizados |
| `mean_price`, `min_price`, `max_price` | Estadísticos adicionales de la distribución |

### `outputs/bucket_summary.csv`

Reporte de cobertura y calidad. Muestra, para cada combinación de destino y segmento, la cantidad de contextos disponibles y qué proporción tiene alta confianza estadística.

| Columna | Descripción |
|---------|-------------|
| `destination_final` | ID del destino |
| `destination_name` | Nombre del destino |
| `price_bucket` | Segmento: `"low"`, `"medium"`, `"high"` |
| `n_contexts` | Número de contextos (combinaciones mes × semana) para este segmento |
| `total_observations` | Total de observaciones diarias acumuladas en esos contextos |
| `high_confidence_pct` | Porcentaje de contextos con ≥ 30 observaciones |

---

## 12. Principales Problemáticas Resueltas

Durante el desarrollo de la exploración inicial se identificaron cinco problemas técnicos que, de no resolverse, impedirían que la clasificación fuera significativa. Se describen a continuación junto con las decisiones de diseño adoptadas en cada caso.

### 1. Comparación de búsquedas con parámetros heterogéneos

**Problema**: el precio total de un hotel varía con la cantidad de noches, habitaciones y personas, haciendo que comparaciones directas sean engañosas.

**Solución**: normalización multiplicativa a precio por persona-habitación-noche, que escala correctamente con todos los parámetros de búsqueda.

### 2. Sesgo por mezcla de categorías de hotel

**Problema**: un z-score calculado sobre la distribución completa del mercado clasifica incorrectamente las búsquedas según su segmento de precio (el segmento Budget siempre aparece como "Deal" y el Premium como "Expensive", independientemente del precio real).

**Solución**: segmentación previa por percentiles de precio (p25 / p75) del propio destino. Cada búsqueda se compara únicamente contra el histórico de su mismo segmento.

### 3. Estacionalidad y variación semanal

**Problema**: el precio de un destino varía significativamente según la época del año y la semana del mes. Una línea de base anual produciría clasificaciones incorrectas en temporadas altas.

**Solución**: granularidad temporal de destino × mes × semana del mes (4 semanas fijas). Esto permite que el sistema reconozca, por ejemplo, que la tercera semana de diciembre en Las Vegas es estructuralmente más cara que la primera.

### 4. Explosión del volumen de datos en la expansión temporal

**Problema**: convertir estadías multi-noche en observaciones diarias multiplicaba el dataset por el factor de noches promedio (~4x), haciendo el pipeline extremadamente lento con iteración fila a fila.

**Solución**: implementación con `numpy.repeat` en lugar de `iterrows`, logrando una reducción de tiempo de ~1000x para este paso.

### 5. Baja densidad de datos en contextos específicos

**Problema**: la combinación de ~26.000 destinos × 12 meses × 4 semanas × 3 segmentos genera millones de contextos teóricos. Con 10.7M de observaciones, la mayoría de los contextos tiene pocas observaciones.

**Solución**: sistema de niveles de confianza (`high / medium / low`) con fallback automático. Si no existe línea de base para el segmento específico, el sistema recurre a la línea de base general del mismo destino y período. Los contextos con menos de 30 observaciones se marcan como `low_confidence` y se informa al usuario.

---

## 13. Limitaciones y Alcance del Enfoque Actual

Las siguientes limitaciones son conocidas y forman parte del alcance definido para esta primera versión. Se documentan para orientar el trabajo en iteraciones futuras.

- **77% de contextos con baja confianza estadística**: la combinación de ~26.000 destinos × 12 meses × 4 semanas × 3 segmentos genera una cantidad de contextos que los 10.7M de observaciones disponibles no pueden cubrir densamente. El sistema responde en todos los casos, pero con menor precisión en destinos pequeños o períodos poco buscados.

- **Clasificación a nivel de mercado, no de hotel individual**: el dataset de tipo `HOTELS` provee únicamente rangos estadísticos del conjunto de hoteles disponibles. La clasificación refiere al promedio del mercado para ese destino y período, no a la oferta de un hotel específico. Esta es la limitación más relevante para una futura evolución del sistema hacia análisis por propiedad.

- **Cobertura parcial del mapping de destinos**: aproximadamente el 40% de los destinos del dataset no tiene un mapeo canónico en `destination_with_nearest.csv` y usa el nombre de ciudad como identificador, lo que puede fragmentar las observaciones de mercados con nombres de ciudad inconsistentes.

- **Ventana histórica acotada (2024–2025)**: el sistema no cuenta con historial previo a 2024. Períodos con comportamiento atípico de precios dentro de esa ventana (eventos masivos, disrupciones de oferta) pueden afectar las distribuciones de referencia.

- **Columna `nights` no validada contra fechas**: la duración de la estadía proviene directamente de la base de datos sin verificación cruzada sistemática contra `date_end - date_start`.

---

## 14. Cómo Ejecutar el Proyecto

### Instalación

```bash
git clone https://github.com/martinid90/id90-hotel-deals-analysis.git
cd id90-hotel-deals-analysis
python -m venv .venv
source .venv/bin/activate      # Linux / macOS
# .venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

### Opción A — Con datos provistos externamente

Los archivos de datos históricos están disponibles en: [Google Drive — Carpeta de datos](https://drive.google.com/drive/folders/1fNs03vOkkO2mVKibHKLmCbzgyatv1yCd?usp=drive_link)

La carpeta contiene:
- `datos_historicos_2024.csv` — datos de búsquedas del año 2024 (~200 MB)
- `datos_historicos_2025.csv` — datos de búsquedas del año 2025 (~200 MB)
- `destination_with_nearest.csv` — mapping de ciudades a destinos canónicos (1.2 MB)

1. Descargar los archivos `datos_historicos_*.csv` y colocarlos en `data/`
2. Ejecutar el pipeline para generar los archivos de outputs:
   ```bash
   python pipeline_build_baselines.py
   ```
3. Iniciar la aplicación:
   ```bash
   streamlit run app.py
   ```

### Opción B — Regenerar desde base de datos interna

```bash
# 1. Configurar credenciales
export DB_HOST=your-dwh-host
export DB_PORT=5432
export DB_USER=your_user
export DB_PASSWORD=your_password
export DB_NAME=your_database

# 2. Extraer datos históricos (puede ejecutarse para distintos años)
python query_historicos.py 2024
python query_historicos.py 2025

# 3. Procesar y generar líneas de base
python pipeline_build_baselines.py

# 4. Iniciar la aplicación
streamlit run app.py
```

### Explorar con el notebook de ejemplo

El notebook `exploratory_analysis.ipynb` carga los datos reales desde `data/datos_historicos_*.csv`, recorre las etapas del pipeline paso a paso y muestra cómo clasificar un precio concreto. Es el punto de partida recomendado para el TP1 de la mentoría DiploDatos 2026.

### Tests

```bash
pytest test_system.py -v
```

---

## 15. Ejemplos de Uso de la Aplicación

Para lanzar la app:

```bash
streamlit run app.py
```

URL: **http://localhost:8501**

### Tabla de interpretación de z-scores

| Z-Score | Clasificación | Acción recomendada |
|---------|---------------|--------------------|
| z < −1.0 | 🟢 Deal | Precio excepcional — reservar ahora |
| −1.0 a −0.5 | 🔵 Good Price | Buen momento para reservar |
| −0.5 a +0.5 | 🟡 Normal Price | Precio estándar del mercado |
| +0.5 a +1.0 | 🟠 Expensive | Considerar otras opciones |
| z > +1.0 | 🔴 Very Expensive | Evitar si es posible |

### Ejemplos verificados

#### NYC — Deal (enero)

| Campo | Valor |
|-------|-------|
| Destino ID | 77 (New York) |
| Check-in | 2025-01-15 |
| Noches / Habitaciones / Adultos / Niños | 2 / 1 / 2 / 0 |
| Precio total | $300 |

Precio normalizado: `$300 / (2 × 1 × 2) = $75`  
Resultado esperado: **Deal** · z ≈ −1.46 · 73% más barato que el promedio

---

#### NYC — Normal Price (enero)

| Campo | Valor |
|-------|-------|
| Destino ID | 77 (New York) |
| Check-in | 2025-01-20 |
| Noches / Habitaciones / Adultos / Niños | 2 / 1 / 2 / 0 |
| Precio total | $730 |

Precio normalizado: `$730 / (2 × 1 × 2) = $182.50`  
Resultado esperado: **Normal Price** · z ≈ 0.0

---

#### Chicago — Deal (familia, verano)

| Campo | Valor |
|-------|-------|
| Destino ID | 60468 (Chicago) |
| Check-in | 2025-06-15 |
| Noches / Habitaciones / Adultos / Niños | 3 / 1 / 2 / 1 |
| Precio total | $400 |

Precio normalizado: `$400 / (3 × 1 × 3) = $44.44`  
Resultado esperado: **Deal** · z ≈ −1.09

---

#### NYC — Expensive (Navidad)

| Campo | Valor |
|-------|-------|
| Destino ID | 77 (New York) |
| Check-in | 2025-12-25 |
| Noches / Habitaciones / Adultos / Niños | 3 / 2 / 3 / 1 |
| Precio total | $3.000 |

Precio normalizado: `$3.000 / (3 × 2 × 4) = $125`  
Resultado esperado: **Very Expensive** · z > +1.0

---

#### NYC — Good Price (estadía corta)

| Campo | Valor |
|-------|-------|
| Destino ID | 77 (New York) |
| Check-in | 2025-03-10 |
| Noches / Habitaciones / Adultos / Niños | 1 / 1 / 1 / 0 |
| Precio total | $85 |

Precio normalizado: `$85 / (1 × 1 × 1) = $85`  
Resultado esperado: **Good Price** · z ≈ −0.6

### Tips de uso

- **Temporada alta**: enero en NYC y diciembre (fiestas) → precios históricamente más altos
- **Mejor precio**: febrero–marzo son los meses más económicos en la mayoría de los destinos
- **Familias con niños**: el precio normalizado baja al dividirse entre más personas; el z-score puede verse más favorable
- **Viaje de negocios**: 1 adulto, estadía corta → precio normalizado alto; comparar con segmento Premium
- **Primera semana del mes**: usualmente más cara que las semanas 2–4

---

## 16. Extensiones Propuestas

El sistema estadístico actual puede ser la base para modelos de aprendizaje automático supervisado, usando las etiquetas generadas por el pipeline como variable objetivo.

### Clasificación multi-clase

Aprender a predecir la categoría (`Deal / Good Price / Normal / Expensive / Very Expensive`) como función directa de los parámetros de búsqueda, sin calcular explícitamente el z-score. Desafío principal: desbalance de clases (las oportunidades de tipo *Deal* representan ~5% de las observaciones) y alta cardinalidad de la variable destino (~26.000 valores).

**Modelos sugeridos**: Random Forest, XGBoost, LightGBM  
**Métricas**: F1-score ponderado, matriz de confusión

### Regresión sobre z-score

Predecir el z-score continuo permite ordenar oportunidades por magnitud. Un z de −2.5 es cualitativamente distinto a un z de −1.1, aunque ambos caigan en la categoría *Deal*.

**Modelos sugeridos**: Gradient Boosting Regressor, Ridge, Lasso  
**Métricas**: RMSE, MAE, R²

### Serie temporal de precios

Predecir la evolución del precio promedio de un destino en el corto plazo. Permite anticipar si conviene reservar ahora o esperar.

**Modelos sugeridos**: Prophet, ARIMA, LSTM  
**Métrica**: MAPE

### Clasificación binaria con calibración de negocio

Simplificar la decisión a `¿reservar ahora? sí/no` con umbral calibrado según el costo de falsos positivos (recomendar un precio que no es una oportunidad real).

---

## Versión y Créditos

**v3.0.0** — Enero 2026 | Segmentación por segmentos de precio, optimizaciones de rendimiento  
**v2.0.0** — Diciembre 2025 | Nueva fórmula de normalización de precios (multiplicativa)  
**v1.0.0** — Diciembre 2024 | Primera versión con z-scores sin segmentación

Proyecto desarrollado en el marco de la Diplomatura en Ciencia de Datos. Los datos pertenecen a ID90Travel y se utilizan con fines académicos.
