"""Configuración central del TP3: rutas, reglas de curación, cascada y detector.

Todas las decisiones metodológicas quedan fijas acá para que el pipeline,
el notebook y la API usen exactamente la misma regla.
"""

import os
from pathlib import Path

# ----------------------------------------------------------------------
# Rutas
# ----------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
# Los CSV históricos completos (~600 MB) no se versionan: se pueden dejar en
# data/ o apuntar a otra carpeta con HOTEL_DATA_DIR.
HISTORICALS_DIR = Path(os.environ.get("HOTEL_DATA_DIR", DATA_DIR))
HISTORICALS_PATTERN = "datos_historicos_*.csv"
SAMPLE_FILE = DATA_DIR / "sample_data_300k.csv.gz"
MAPPING_FILE = DATA_DIR / "destination_with_nearest.csv"
TEST_SET_DIR = DATA_DIR / "test_set"

OUTPUT_DIR = ROOT_DIR / "outputs"          # tablas en outputs/<source>/
ARTIFACTS_ROOT = ROOT_DIR / "artifacts"     # baselines en artifacts/<source>/


def output_dir(source):
    return OUTPUT_DIR / source


def artifacts_dir(source):
    return ARTIFACTS_ROOT / source


def default_artifacts_dir():
    """La API sirve los artefactos del dataset completo si existen; si no, los de la muestra."""
    env = os.environ.get("HOTEL_ARTIFACTS_DIR")
    if env:
        return Path(env)
    full = artifacts_dir("full")
    return full if (full / "params.json").exists() else artifacts_dir("sample")

SEED = 42

# ----------------------------------------------------------------------
# Split temporal
# ----------------------------------------------------------------------
TRAIN_YEAR = 2024   # historia que ven los detectores
TEST_YEAR = 2025    # mercado "futuro" sobre el que se evalúa

# ----------------------------------------------------------------------
# Curación
# ----------------------------------------------------------------------
MAX_NIGHTS = 30
MAX_PRICE_RAW = 50_000          # USD totales; por encima son errores de carga/moneda
PRICE_STD_FLOOR = 1.0           # USD por habitación-noche-persona; debajo es error de dato
WINSOR_QUANTILE = 0.999         # corte superior, calibrado SOLO con train

# ----------------------------------------------------------------------
# Contexto y cascada de fallback
# ----------------------------------------------------------------------
# Soporte mínimo: 30 BÚSQUEDAS INDEPENDIENTES (n_records = filas únicas),
# no demanda ponderada por count_repeated. Regla única para todo el TP3.
MIN_SUPPORT = 30
SUPPORT_COLUMN = "n_records"

# Niveles en orden de especificidad. El primero con soporte suficiente decide.
CASCADE_LEVELS = [
    ("L1_dest_mes_semana_estadia", ["destination_final", "month", "week_in_month", "stay_duration"]),
    ("L2_dest_mes_estadia", ["destination_final", "month", "stay_duration"]),
    ("L3_dest_mes", ["destination_final", "month"]),
    ("L4_dest_estadia", ["destination_final", "stay_duration"]),
    ("L5_dest", ["destination_final"]),
    ("L6_pais_mes_estadia", ["country_code", "month", "stay_duration"]),
]
NO_SUPPORT_LEVEL = "L7_sin_soporte"

# Nombres legibles de cada nivel (explicación de la API y gráficos)
LEVEL_LABELS = {
    "L1_dest_mes_semana_estadia": "destino × mes × semana × estadía",
    "L2_dest_mes_estadia": "destino × mes × estadía",
    "L3_dest_mes": "destino × mes",
    "L4_dest_estadia": "destino × estadía",
    "L5_dest": "destino",
    "L6_pais_mes_estadia": "país × mes × estadía",
    "L7_sin_soporte": "sin soporte",
}

# ----------------------------------------------------------------------
# Detector híbrido (regla adoptada en TP2)
# ----------------------------------------------------------------------
Z_LOG_THRESHOLD = -1.0
MIN_DISCOUNT = 0.20
MIN_STD_LOG = 0.05              # piso de dispersión: evita z gigantes en mercados planos

# Regla naive por mediana
NAIVE_MEDIAN_DISCOUNT = 0.20

# ----------------------------------------------------------------------
# Machine learning
# ----------------------------------------------------------------------
ML_TOP_CATEGORIES = 250         # destinos / países más frecuentes como categoría propia
ML_RF_MAX_TRAIN_ROWS = 300_000  # RandomForest se entrena sobre una submuestra
