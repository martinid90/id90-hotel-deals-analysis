"""Configuración central del TP3 (versión 2).

Todos los parámetros que cambian resultados están acá, para que la corrida
sea trazable: si cambiás algo, cambiás un solo lugar y queda versionado.
Las rutas se pueden pisar con variables de entorno (útil en Docker).
"""
from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
# Este archivo vive en <proyecto>/src/ofertas_hoteles/config.py
PROJECT_DIR = Path(os.getenv("TP3_PROJECT_DIR", Path(__file__).resolve().parents[2]))
# El proyecto vive en <repo>/entregas/grupo_01/tp3_pupi_v2 → los CSV crudos en <repo>/data
REPO_DIR = PROJECT_DIR.parents[2] if len(PROJECT_DIR.parents) >= 3 else PROJECT_DIR

RAW_DIR = Path(os.getenv("TP3_RAW_DIR", REPO_DIR / "data"))           # datos_historicos_*.csv (pesados, no se suben)
DATA_DIR = Path(os.getenv("TP3_DATA_DIR", PROJECT_DIR / "data"))       # datos livianos que sí se entregan
MODELS_DIR = Path(os.getenv("TP3_MODELS_DIR", PROJECT_DIR / "models"))  # artefactos que usa la API
OUTPUTS_DIR = Path(os.getenv("TP3_OUTPUTS_DIR", PROJECT_DIR / "outputs"))
INTERIM_DIR = Path(os.getenv("TP3_INTERIM_DIR", PROJECT_DIR / "data" / "interim"))  # muestras intermedias (no se suben)

MAPPING_PATH = Path(os.getenv("TP3_MAPPING_PATH", DATA_DIR / "destination_with_nearest.csv"))
RAW_FILES = {2024: "datos_historicos_2024.csv", 2025: "datos_historicos_2025.csv"}

# ---------------------------------------------------------------------------
# Muestreo (pensado para correr en una compu con poca RAM)
# ---------------------------------------------------------------------------
SEED = 42
FRAC_TRAIN_2024 = float(os.getenv("TP3_FRAC_TRAIN", 0.20))  # 20% de las búsquedas de 2024 (~500 mil)
FRAC_2025 = float(os.getenv("TP3_FRAC_2025", 0.20))          # 20% de las búsquedas de 2025 (~530 mil)
CHUNKSIZE = 200_000

# Partición de 2025 en tres pools disjuntos (por grupo destino × fecha de check-in)
POOL_SHARES = {"mercado": 0.40, "val": 0.30, "test": 0.30}

# ---------------------------------------------------------------------------
# Unidad de precio
# ---------------------------------------------------------------------------
# "habitacion_noche": avg_price_average tal cual (la evidencia muestra que ya es precio
#                     por habitación-noche: elasticidad a noches ≈ 0,05 y a habitaciones ≈ 0,02).
# "formula_completa": avg_price_average / (noches × habitaciones × personas) (fórmula de la consigna).
PRICE_UNIT = os.getenv("TP3_PRICE_UNIT", "habitacion_noche")

# ---------------------------------------------------------------------------
# Soporte y fallback
# ---------------------------------------------------------------------------
# .csv.gz sin marca de tiempo: si el contenido no cambia, el archivo es idéntico byte a byte (git no lo marca)
GZ = {"method": "gzip", "mtime": 0}

MIN_SUPPORT = 30  # búsquedas distintas mínimas para confiar en una referencia

# Niveles de contexto, del más fino al más grueso.
LEVELS_A = [
    ("destino_mes", ["destination_final", "month"]),
    ("destino", ["destination_final"]),
    ("pais_mes", ["cc", "month"]),
    ("pais", ["cc"]),
]
LEVELS_B = [("destino_mes_bucket", ["destination_final", "month", "price_bucket"])] + LEVELS_A
LEVELS_GRUPO = [
    ("destino_mes_semana_bucket", ["destination_final", "month", "week_in_month", "price_bucket"]),
    ("destino_mes_bucket", ["destination_final", "month", "price_bucket"]),
    ("destino", ["destination_final"]),
]

# ---------------------------------------------------------------------------
# Parámetros fijos del detector propuesto (reglas de negocio, no se tunean)
# ---------------------------------------------------------------------------
K_MAD = 1.4826        # hace que el MAD sea comparable a un desvío estándar
MAD_MIN = 0.05        # piso del MAD en log (≈5%) para contextos casi sin dispersión
DESC_MIN = 0.20       # descuento mínimo para que una oferta sea relevante
FACTOR_SOSP = 0.20    # precio < 20% del típico → probable error de carga

# ---------------------------------------------------------------------------
# Test set controlado
# ---------------------------------------------------------------------------
ANCHOR_TOL = 0.10                  # ancla = precio a ±10% de la mediana de mercado 2025
FACTORS_POS = [0.40, 0.50, 0.60, 0.70]          # -60% a -30% → oferta clara (etiqueta 1)
FACTORS_GRIS = [0.80, 0.90]                      # -20% y -10% → zona gris (sin etiqueta)
FACTORS_NEG = [1.00, 1.10, 1.20, 1.30, 1.50]     # sin cambio o más caro → no oferta (etiqueta 0)
FACTORS_ERROR = [0.10]                           # -90% → error de carga (se espera "sospechoso")
N_ANCHORS_TEST = 3000
N_ANCHORS_VAL = 2000
N_REALES = 20000

# Restricción de producto al elegir umbrales: no marcar más del 10% de los precios reales
MAX_ALERT_RATE = 0.10

# ---------------------------------------------------------------------------
# Presentación: modelos de la comparación principal (el resto va al anexo)
# ---------------------------------------------------------------------------
MODELOS_PRINCIPALES = ["1_aleatorio", "2_mediana_regla", "3_propuesto_robusto_A", "5_isolation_forest"]
