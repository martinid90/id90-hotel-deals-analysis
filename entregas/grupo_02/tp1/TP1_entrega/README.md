# TP1 — Exploración de Mercado y Homogeneidad de Precios
## Diplomatura en Ciencia de Datos · Mentoría ID90Travel

Este directorio contiene todo el material necesario para ejecutar de forma autónoma el notebook definitivo de entrega del **Trabajo Práctico 1 (TP1)**: definición de mercados hoteleros, auditoría de calidad, mapeo canónico de destinos, análisis multidimensional de varianza (SNR) y evaluación de confiabilidad de baselines.

---

## Estructura del Paquete de Entrega

```text
TP1_entrega/
├── TP1_exploracion_mercado.ipynb    # Notebook definitivo ejecutable celda por celda
├── auxiliary_functions.py           # Funciones de validación, estandarización, mapeo y baselines
├── config.py                        # Configuración de rutas, umbrales y parámetros
├── database.py                      # Utilitario para construcción de la base SQLite local
├── pipeline_build_baselines.py      # Pipeline de cálculo vectorizado de baselines completos
├── requirements.txt                 # Dependencias y librerías requeridas
├── README.md                        # Esta guía de uso y ejecución
│
├── data/
│   ├── destination_with_nearest.csv        # Mapeo canónico de destinos geográficos con correcciones
│   ├── destination_with_nearest_backup.csv # Backup del mapeo original (para análisis de remapeos)
│   ├── datos_historicos_2024.csv           # [Descargar de Drive si no está presente, ~260MB]
│   └── datos_historicos_2025.csv           # [Descargar de Drive si no está presente, ~280MB]
│
├── outputs/                                # Baselines precomputados sobre 5.15M de registros
│   ├── market_baselines.csv                # 721.348 contextos con media, desvío y flag de confiabilidad
│   ├── price_distribution.csv              # Percentiles p25/p50/p75 por destino
│   └── bucket_summary.csv                  # Resumen por gama tarifaria (budget/mid/premium)
│
└── TP1/outputs/
    └── maps/                               # Mapas interactivos HTML generados
        ├── 05_mapa_destinos_canonicos.html
        └── 06_mapa_remapeo_antes_despues.html
```

---

## Guía de Instalación y Ejecución

### 1. Entorno Virtual y Dependencias
Recomendado Python 3.10, 3.11 o 3.12:
```bash
# Crear entorno virtual (opcional pero recomendado)
python -m venv .venv
source .venv/bin/activate  # En Linux/Mac
# o en Windows: .venv\Scripts\activate

# Instalar librerías
pip install -r requirements.txt
```

### 2. Archivos de Datos Históricos
- Los archivos `data/destination_with_nearest.csv` y los baselines precalculados en `outputs/` **ya están incluidos en esta carpeta**.
- Si deseas reejecutar la muestra desde los datos crudos, asegúrate de colocar los archivos `datos_historicos_2024.csv` y `datos_historicos_2025.csv` (disponibles en el Google Drive de la materia) dentro de la carpeta `data/`.

### 3. Ejecución del Notebook
Puedes abrir y ejecutar el notebook directamente con Jupyter Lab, Jupyter Notebook o VS Code:
```bash
jupyter notebook TP1_exploracion_mercado.ipynb
```
El notebook está optimizado para:
- Detectar automáticamente si existe la base de datos `data/hotel_data.db` o leer directamente una muestra representativa de 300.000 filas de los CSVs crudos.
- Ejecutarse en menos de **30 segundos** consumiendo menos de **1.5 GB de memoria RAM**.

---

## Principales Hallazgos y Resultados del TP1

1. **Definición de Mercado Hotelero**:
   - Queda delimitado por la proximidad geográfica al **destino canónico (`destination_final`)**, resolviendo la dispersión de más de 26.000 nombres crudos a través del mapeo Haversine con correcciones manuales en mercados contiguos.
   
2. **Contexto de Comparabilidad**:
   - Dos precios son estrictamente comparables cuando coinciden en: **Destino Canónico $\times$ Mes $\times$ Semana del Mes $\times$ Duración de Estadía** (por el descuento no lineal por volumen que reduce hasta un 91% la tarifa diaria para estadías de más de 7 noches).

3. **Confiabilidad de Baselines y Ley de Pareto**:
   - Aunque solo el **27.4% de los contextos teóricos** tiene $N \ge 30$ observaciones (197.460 contextos), estas celdas concentran el **96.8% del tráfico real de usuarios**.
   - Para el 3.2% de demanda restante en destinos poco frecuentes (*long-tail*), se aplica **Shrinkage Jerárquico** (media mensual / anual del destino) para garantizar robustez estadística.

4. **Estabilidad Interanual (2024 vs 2025)**:
   - Curva de descuento por estadía: **$r = 1.000$**.
   - Patrón por día de la semana: **$r = 0.987$**.
   - Jerarquía relativa entre destinos: **$r = 0.828$**.
