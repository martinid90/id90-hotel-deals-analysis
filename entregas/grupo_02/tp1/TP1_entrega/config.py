# config.py
# Configuración centralizada para el sistema de detección de deals

import os
import logging
from pathlib import Path


# ========================================
# LOGGING CONFIGURATION
# ========================================

LOG_LEVEL = logging.INFO  # Optimizado: reducido de DEBUG para menos verbosidad
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# ========================================
# PATHS
# ========================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"

# Subdirectorios
PRICE_HISTORICALS_DIR = DATA_DIR  # Archivos directamente en data/
LOGS_DIR = OUTPUT_DIR / "logs"

# Archivos
DESTINATION_MAPPING_FILE = DATA_DIR / "destination_with_nearest.csv"
BASELINES_FILE = OUTPUT_DIR / "market_baselines.csv"
PRICE_DISTRIBUTION_FILE = OUTPUT_DIR / "price_distribution.csv"
BUCKET_SUMMARY_FILE = OUTPUT_DIR / "bucket_summary.csv"

# AWS paths (si se usa S3)
AWS_DATA_DIR = "data"
AWS_BASELINES_FILE = os.path.join(AWS_DATA_DIR, "market_baselines.csv")

# Crear directorios si no existen
for directory in [DATA_DIR, OUTPUT_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


# ========================================
# DATABASE CONFIG
# ========================================
# Configurar via variables de entorno:
#   export DB_HOST=your-host
#   export DB_PORT=5432
#   export DB_USER=your_user
#   export DB_PASSWORD=your_password
#   export DB_NAME=your_database

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'your-dwh-host.example.com'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'your_database'),
    'user': os.getenv('DB_USER', 'your_user'),
    'password': os.getenv('DB_PASSWORD', '')
}


# ========================================
# COLUMN NAMES
# ========================================

# Columnas de entrada (raw data)
COLS_INPUT = {
    'city': 'city',
    'state': 'state',
    'country': 'country',
    'date_start': 'date_start',
    'date_end': 'date_end',
    'nights': 'nights',
    'number_of_rooms': 'number_of_rooms',
    'number_of_adults': 'number_of_adults',
    'number_of_kids': 'number_of_kids',
    'count_repeated': 'count_repeated',
    'avg_hotel_count': 'avg_hotel_count',
    'min_hotel_count': 'min_hotel_count',
    'max_hotel_count': 'max_hotel_count',
    'avg_price_average': 'avg_price_average',
    'max_price_high': 'max_price_high',
    'min_price_low': 'min_price_low'
}

# Columnas estandarizadas
COLS_STANDARDIZED = {
    'avg_price_average_std': 'avg_price_average_std',
    'max_price_high_std': 'max_price_high_std',
    'min_price_low_std': 'min_price_low_std'
}

# Columnas de baselines finales
COLS_BASELINES = [
    'destination_final',
    'month',
    'week_in_month',
    'mean_price_std',
    'std_price_std',
    'min_price_std',
    'max_price_std',
    'count_obs',
    'low_confidence'
]

# Columnas de baselines con buckets
COLS_BASELINES_WITH_BUCKETS = [
    'destination_final',
    'destination_name',
    'month',
    'week_in_month',
    'price_bucket',
    'mean_price_std',
    'std_price_std',
    'min_price_std',
    'max_price_std',
    'count_obs',
    'low_confidence'
]


# ========================================
# THRESHOLDS
# ========================================

# Classification thresholds (z-score)
THRESHOLDS = {
    'deal': -1.0,           # z < -1.0 → Deal
    'good_price': -0.5,     # -1.0 <= z < -0.5 → Good Price
    'normal_upper': 0.5     # z > 0.5 → Expensive
}

# Classification Labels
CLASSIFICATION_LABELS = {
    'deal': 'Deal',
    'good_price': 'Good Price',
    'normal': 'Normal Price',
    'expensive': 'Expensive',
    'insufficient_data': 'Insufficient Data'
}


# ========================================
# VALIDATION PARAMS
# ========================================

MIN_OBSERVATIONS = 30       # Mínimo de observaciones para baseline confiable
MIN_STD_PRICE = 10.0        # Desviación estándar mínima
USE_DYNAMIC_MIN_STD = True  # Usar % del mean como mínimo
DYNAMIC_MIN_STD_PERCENT = 0.10  # 10% del mean


# ========================================
# STANDARDIZATION RULES
# ========================================

# Reglas para estandarización de precios
# Nueva fórmula: price_std = price / (nights * rooms * (adults + kids))
# 
# Interpretación económica:
#   - Precio por "room-night-person"
#   - Permite comparar:
#       * 1 noche, 1 habitación, 1 adulto
#       * vs 3 noches, 2 habitaciones, 4 personas
#   - Si un parámetro está por debajo del threshold, se usa fallback
#   - adults siempre >= 1 en datos reales
#   - kids puede ser 0 (no pasa nada, suma 0 a adults)

STANDARDIZATION_RULES = {
    'nights': {'threshold': 1, 'fallback': 0},
    'number_of_rooms': {'threshold': 1, 'fallback': 0},
    'number_of_adults': {'threshold': 1, 'fallback': 1},
    'number_of_kids': {'threshold': 0, 'fallback': 0}
}


# ========================================
# TEMPORAL FEATURES
# ========================================

# Rangos de semanas del mes
WEEK_RANGES = {
    1: (1, 7),
    2: (8, 15),
    3: (16, 22),
    4: (23, 31)
}


# ========================================
# FILE PATTERNS
# ========================================

HISTORICALS_FILE_PATTERN = "datos_historicos_*.csv"


# ========================================
# PRICE BUCKET CONFIGURATION
# ========================================

# Feature flag para activar/desactivar buckets
ENABLE_PRICE_BUCKETS = True

# Percentiles para clasificación de buckets
BUCKET_PERCENTILES = {
    'low': 25,      # <= p25
    'high': 75      # >= p75
    # medium: entre p25 y p75
}

# Bucket Labels
BUCKET_LABELS = {
    'low': 'Budget',
    'medium': 'Mid-Range',
    'high': 'Premium'
}

# Mínimo de observaciones por bucket para considerarlo válido
MIN_OBSERVATIONS_PER_BUCKET = 10

# Estrategia de fallback cuando un bucket tiene pocas observaciones
BUCKET_FALLBACK_STRATEGY = 'use_overall'  # 'use_overall' o 'merge_adjacent'


# ========================================
# APP CONFIG
# ========================================

APP_CONFIG = {
    'title': '🏨 Hotel Deals Detector',
    'port': 8501,
    'host': '0.0.0.0'
}


# ========================================
# UTILITY FUNCTIONS
# ========================================

def get_week_in_month(day: int) -> int:
    """Retorna la semana del mes basada en el día."""
    for week, (start, end) in WEEK_RANGES.items():
        if start <= day <= end:
            return week
    return 4


def get_confidence_level(count_obs: int) -> str:
    """Determina nivel de confianza basado en observaciones."""
    if count_obs >= 100:
        return 'high'
    elif count_obs >= MIN_OBSERVATIONS:
        return 'medium'
    else:
        return 'low'
