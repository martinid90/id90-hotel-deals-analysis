# auxiliary_functions.py
# Funciones auxiliares para el sistema de detección de deals

import pandas as pd
import numpy as np
from scipy import stats
import glob
from pathlib import Path
import logging
import config

# Configurar logging
logging.basicConfig(
    level=logging.INFO,  # Optimizado: INFO en lugar de DEBUG
    format='%(asctime)s - %(levelname)s - %(message)s'
)


# ========================================
# DATA LOADING
# ========================================

def load_all_historicals(data_path=None):
    """
    Loads all historical CSV files from the specified directory.
    
    Args:
        data_path (Path, optional): Directory path (default: config.PRICE_HISTORICALS_DIR)
    
    Returns:
        pd.DataFrame: Combined DataFrame with all historical records
    
    Raises:
        FileNotFoundError: If no CSV files found in directory
    """
    if data_path is None:
        data_path = config.PRICE_HISTORICALS_DIR
    
    data_path = Path(data_path)
    pattern = str(data_path / config.HISTORICALS_FILE_PATTERN)
    files = glob.glob(pattern)
    
    if not files:
        raise FileNotFoundError(f"No files found in {data_path}")
    
    logging.info(f"Loading {len(files)} historical files...")
    
    dfs = []
    for file in sorted(files):
        df_temp = pd.read_csv(file)
        df_temp['source_file'] = Path(file).name
        dfs.append(df_temp)
        logging.debug(f"  ✓ {Path(file).name}: {len(df_temp):,} registros")
    
    df_combined = pd.concat(dfs, ignore_index=True)
    logging.info(f"Total loaded: {len(df_combined):,} records")
    
    return df_combined


def load_destination_mapping(mapping_path=None):
    """
    Loads the city-to-destination mapping file.
    
    Args:
        mapping_path: Path al CSV (default: config.DESTINATION_MAPPING_FILE)
    
    Returns:
        DataFrame con mapping
    """
    if mapping_path is None:
        mapping_path = config.DESTINATION_MAPPING_FILE
    
    if not Path(mapping_path).exists():
        logging.warning(f"Mapping no encontrado: {mapping_path}")
        return None
    
    mapping_df = pd.read_csv(mapping_path)
    logging.info(f"Mapping cargado: {len(mapping_df):,} registros")
    logging.debug(f"  Reducción: {mapping_df['city'].nunique()} → {mapping_df['nearest_destination_id'].nunique()} destinos")
    
    return mapping_df


def validate_data(df):
    """
    Filtra registros con datos erróneos (denominador = 0).
    Elimina registros donde: nights <= 0 OR rooms <= 0 OR (adults + kids) <= 0
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame con datos históricos
        
    Returns:
    --------
    pd.DataFrame con registros válidos
    """
    initial_count = len(df)
    
    # Filtrar registros erróneos
    valid_df = df[
        (df['nights'] > 0) & 
        (df['number_of_rooms'] > 0) & 
        ((df['number_of_adults'] + df['number_of_kids']) > 0)
    ].copy()
    
    removed_count = initial_count - len(valid_df)
    
    if removed_count > 0:
        logging.warning(f"Registros eliminados por datos erróneos: {removed_count} ({100*removed_count/initial_count:.2f}%)")
        logging.debug(f"  - nights <= 0: {len(df[df['nights'] <= 0])}")
        logging.debug(f"  - rooms <= 0: {len(df[df['number_of_rooms'] <= 0])}")
        logging.debug(f"  - (adults + kids) <= 0: {len(df[(df['number_of_adults'] + df['number_of_kids']) <= 0])}")
    else:
        logging.info("✓ Todos los registros son válidos (sin denominadores = 0)")
    
    logging.info(f"Registros válidos: {len(valid_df):,} ({100*len(valid_df)/initial_count:.1f}%)")
    
    return valid_df


def apply_destination_mapping(df, mapping_df):
    """
    Aplica mapping de destinaciones usando reference (country_code-state_code-city) + city.
    
    Args:
        df: DataFrame con columnas 'country_code', 'state', 'city'
        mapping_df: DataFrame con columnas 'reference', 'city', 'nearest_destination_id', 'nearest_destination_name'
    
    Returns:
        DataFrame con 'destination_final' (ID) y 'destination_name' (nombre)
    """
    if mapping_df is None:
        logging.warning("No hay mapping disponible, usando 'city' como destino")
        df['destination_final'] = df['city']
        df['destination_name'] = df['city']
        return df
    
    # Mapeo de nombres de estados a códigos
    STATE_CODES = {
        'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
        'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA',
        'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
        'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
        'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO',
        'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ',
        'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH',
        'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
        'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT',
        'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'
    }
    
    # Construir reference como 'country_code - state_code - city'
    df['state_code'] = df['state'].map(STATE_CODES)
    df['reference'] = df['country_code'] + ' - ' + df['state_code'].fillna('') + ' - ' + df['city']
    
    # Optimización: crear índice temporal en mapping para merge más rápido
    mapping_indexed = mapping_df[['reference', 'city', 'nearest_destination_id', 'nearest_destination_name']].copy()
    mapping_indexed = mapping_indexed.set_index(['reference', 'city'])
    
    # Merge por 'reference' + 'city' con índice (más rápido)
    df = df.merge(
        mapping_indexed,
        left_on=['reference', 'city'],
        right_index=True,
        how='left',
        copy=False
    )
    
    # Usar nearest_destination_id como destination_final (clave interna)
    # Usar nearest_destination_name para display
    df['destination_final'] = df['nearest_destination_id'].fillna(df['city'])
    df['destination_name'] = df['nearest_destination_name'].fillna(df['city'])
    
    matched = df['nearest_destination_id'].notna().sum()
    total = len(df)
    
    logging.info(f"Mapping aplicado: {matched:,}/{total:,} registros ({100*matched/total:.1f}%)")
    logging.info(f"Destinos únicos: {df['destination_final'].nunique():,}")
    
    return df


def evaluate_hotel_price(destination_final, month, week_in_month, price_std, baselines_df):
    """
    Evalúa un precio contra los baselines y clasifica.
    
    Args:
        destination_final: Destino
        month: Mes (1-12)
        week_in_month: Semana del mes (1-4)
        price_std: Precio estandarizado
        baselines_df: DataFrame de baselines
    
    Returns:
        dict con classification, z_score, baseline_info
    """
    # Buscar baseline
    baseline_row = baselines_df[
        (baselines_df['destination_final'] == destination_final) &
        (baselines_df['month'] == month) &
        (baselines_df['week_in_month'] == week_in_month)
    ]
    
    if baseline_row.empty:
        return {
            'classification': 'Insufficient Data',
            'z_score': None,
            'baseline_info': None,
            'confidence': 'low'
        }
    
    baseline = baseline_row.iloc[0]
    
    # Calcular z-score
    if baseline['std_price_std'] == 0 or pd.isna(baseline['std_price_std']):
        z_score = 0.0
    else:
        z_score = (price_std - baseline['mean_price_std']) / baseline['std_price_std']
    
    # Clasificar
    classification = classify_deal(z_score)
    
    # Confianza
    confidence = 'low' if baseline.get('low_confidence', False) else 'high'
    
    return {
        'classification': classification,
        'z_score': z_score,
        'baseline_info': {
            'mean': baseline['mean_price_std'],
            'std': baseline['std_price_std'],
            'count': baseline.get('count_obs', 0)
        },
        'confidence': confidence
    }


def evaluate_hotel_with_bucket_classification(destination_final, month, week_in_month, 
                                               price_std, baselines_df, price_dist_df=None,
                                               enable_buckets=None):
    """
    Evaluates hotel price using bucket-aware classification for fair market comparison.
    
    This function implements a 6-step process:
    1. Determines the hotel's price bucket based on destination percentiles
    2. Searches for bucket-specific baseline (destination + month + week + bucket)
    3. Falls back to general baseline if bucket-specific data unavailable
    4. Calculates z-score: (price - mean) / std
    5. Classifies deal quality based on z-score thresholds
    6. Returns comprehensive result with confidence indicators
    
    Args:
        destination_final (str): Internal destination ID (e.g., 'US-NV-Las Vegas')
        month (int): Month of check-in (1-12)
        week_in_month (int): Week within month (1-4)
        price_std (float): Standardized price ($/room-night-person)
        baselines_df (pd.DataFrame): DataFrame with historical baselines
        price_dist_df (pd.DataFrame, optional): Destination percentiles (required for buckets)
        enable_buckets (bool, optional): Enable bucket classification (default: config.ENABLE_PRICE_BUCKETS)
    
    Returns:
        dict: {
            'classification': str - Deal category ('Deal', 'Good Price', 'Normal Price', 'Expensive', 'Insufficient Data')
            'is_deal': bool - True if z-score < -1.0
            'z_score': float - Statistical score vs market (negative = below average)
            'price_bucket': str - Hotel category ('low'=Budget, 'medium'=Mid-Range, 'high'=Premium)
            'relative_price_index': float - price_std / market_median (e.g., 0.8 = 20% below median)
            'baseline_info': dict - Market statistics {'mean': float, 'std': float, 'count': int, 'bucket': str}
            'market_percentiles': dict - {'p25': float, 'p50': float, 'p75': float}
            'confidence': str - 'low', 'medium', or 'high' based on data quality
            'used_fallback': bool - True if bucket-specific baseline unavailable
            'message': str - Optional error/warning message
        }
    
    Examples:
        >>> result = evaluate_hotel_with_bucket_classification(
        ...     destination_final='US-NV-Las Vegas',
        ...     month=6, week_in_month=2,
        ...     price_std=45.0,
        ...     baselines_df=baselines,
        ...     price_dist_df=price_dist,
        ...     enable_buckets=True
        ... )
        >>> result['classification']
        'Deal'
        >>> result['price_bucket']
        'medium'
        >>> result['z_score']
        -1.25
    
    Notes:
        - Confidence degrades to 'medium' when using fallback baseline
        - Std deviation uses 10% of mean as fallback when std=0
        - Requires price_dist_df when enable_buckets=True
        - Falls back to non-bucket evaluation if price_dist_df is None
    """
    if enable_buckets is None:
        enable_buckets = config.ENABLE_PRICE_BUCKETS
    
    # Si buckets no están habilitados, usar función original
    if not enable_buckets or price_dist_df is None:
        result = evaluate_hotel_price(destination_final, month, week_in_month, price_std, baselines_df)
        result['is_deal'] = is_deal(result['z_score'])
        result['price_bucket'] = None
        result['relative_price_index'] = None
        result['market_percentiles'] = None
        result['used_fallback'] = False
        return result
    
    # PASO 1: Determinar bucket del hotel
    dest_dist = price_dist_df[price_dist_df['destination_final'] == destination_final]
    
    if dest_dist.empty:
        return {
            'classification': 'Insufficient Data',
            'is_deal': False,
            'z_score': None,
            'price_bucket': None,
            'relative_price_index': None,
            'market_percentiles': None,
            'baseline_info': None,
            'confidence': 'low',
            'used_fallback': False,
            'message': f'No price distribution available for destination {destination_final}'
        }
    
    dist = dest_dist.iloc[0]
    p25 = dist['p25']
    p50 = dist['p50']
    p75 = dist['p75']
    
    # Clasificar en bucket
    if price_std <= p25:
        price_bucket = 'low'
    elif price_std < p75:
        price_bucket = 'medium'
    else:
        price_bucket = 'high'
    
    logging.debug(f"Hotel classified into '{price_bucket}' bucket (price={price_std:.2f}, p25={p25:.2f}, p75={p75:.2f})")
    
    # STEP 2: Search for bucket-specific baseline
    baseline_row = baselines_df[
        (baselines_df['destination_final'] == destination_final) &
        (baselines_df['month'] == month) &
        (baselines_df['week_in_month'] == week_in_month) &
        (baselines_df['price_bucket'] == price_bucket)
    ]
    
    # Fallback: if no baseline for this bucket, use general baseline
    if baseline_row.empty:
        logging.warning(f"No baseline for bucket '{price_bucket}', using fallback...")
        baseline_row = baselines_df[
            (baselines_df['destination_final'] == destination_final) &
            (baselines_df['month'] == month) &
            (baselines_df['week_in_month'] == week_in_month)
        ]
        used_fallback = True
    else:
        used_fallback = False
    
    # If still no baseline, return insufficient data
    if baseline_row.empty:
        return {
            'classification': 'Insufficient Data',
            'is_deal': False,
            'z_score': None,
            'price_bucket': price_bucket,
            'relative_price_index': None,
            'market_percentiles': {'p25': p25, 'p50': p50, 'p75': p75},
            'baseline_info': None,
            'confidence': 'low',
            'used_fallback': used_fallback,
            'message': f'No baseline available for destination {destination_final}, month {month}, week {week_in_month}'
        }
    
    baseline = baseline_row.iloc[0]
    
    # PASO 3: Calcular z-score
    mean = baseline['mean_price_std']
    std = baseline['std_price_std']
    
    if std == 0 or pd.isna(std):
        std = mean * 0.10  # Fallback: 10% del mean
    
    z_score = (price_std - mean) / std
    
    # PASO 4: Clasificar
    classification = classify_deal(z_score)
    is_deal_flag = is_deal(z_score)
    
    # PASO 5: Confianza
    if baseline.get('low_confidence', False):
        confidence = 'low'
    elif used_fallback:
        confidence = 'medium'
    else:
        confidence = 'high'
    
    # PASO 6: Relative Price Index
    relative_price_index = (price_std / p50) if p50 > 0 else None
    
    # PASO 7: Construir respuesta
    return {
        'classification': classification,
        'is_deal': is_deal_flag,
        'z_score': z_score,
        'price_bucket': price_bucket,
        'relative_price_index': relative_price_index,
        'baseline_info': {
            'mean': mean,
            'std': std,
            'count': baseline.get('count_obs', 0),
            'bucket': baseline.get('price_bucket', 'mixed')
        },
        'market_percentiles': {
            'p25': p25,
            'p50': p50,
            'p75': p75
        },
        'confidence': confidence,
        'used_fallback': used_fallback,
        'message': f"Hotel {price_bucket} comparado contra baseline de su categoría"
    }


# ========================================
# STANDARDIZATION
# ========================================

def calculate_price_std(row, col_name):
    """
    Calculates standardized price per unit (price per room-night-person).
    
    Formula: price_std = price_raw / (nights * rooms * (adults + kids))
    
    Economic Interpretation:
    - Price for 1 night, 1 room, 1 person
    - Enables comparison across searches with different configurations
    - If adults + kids = 0, uses 1 as fallback (adults always >= 1)
    
    Args:
        row (pd.Series): DataFrame row
        col_name (str): Column name to standardize
    
    Returns:
        float: Standardized price (price per room-night-person)
    
    Example:
        >>> row = {'nights': 3, 'number_of_rooms': 2, 'number_of_adults': 2, 
        ...        'number_of_kids': 1, 'avg_price_average': 450}
        >>> calculate_price_std(row, 'avg_price_average')
        25.0  # 450 / (3 * 2 * 3)
    """
    rules = config.STANDARDIZATION_RULES
    
    nights = row['nights'] if row['nights'] > rules['nights']['threshold'] else rules['nights']['fallback']
    rooms = row['number_of_rooms'] if row['number_of_rooms'] > rules['number_of_rooms']['threshold'] else rules['number_of_rooms']['fallback']
    adults = row['number_of_adults'] if row['number_of_adults'] > rules['number_of_adults']['threshold'] else rules['number_of_adults']['fallback']
    kids = row['number_of_kids']
    
    # Nueva fórmula: producto en lugar de suma
    # nights * rooms * (adults + kids)
    total_persons = adults + kids
    if total_persons == 0:
        total_persons = 1
    
    denominator = nights * rooms * total_persons
    if denominator == 0:
        denominator = 1
    
    price_std = row[col_name] / denominator
    
    return price_std


def standardize_prices(df):
    """
    Aplica estandarización a columnas de precio.
    Versión optimizada: operaciones vectorizadas en lugar de apply row-by-row.
    
    Args:
        df: DataFrame con precios crudos
    
    Returns:
        DataFrame con columnas *_std
    """
    df = df.copy()
    
    # Operaciones vectorizadas (mucho más rápido que apply)
    rules = config.STANDARDIZATION_RULES
    
    nights = df['nights'].where(df['nights'] > rules['nights']['threshold'], rules['nights']['fallback'])
    rooms = df['number_of_rooms'].where(df['number_of_rooms'] > rules['number_of_rooms']['threshold'], rules['number_of_rooms']['fallback'])
    adults = df['number_of_adults'].where(df['number_of_adults'] > rules['number_of_adults']['threshold'], rules['number_of_adults']['fallback'])
    kids = df['number_of_kids'].fillna(0)
    
    total_persons = (adults + kids).replace(0, 1)
    denominator = (nights * rooms * total_persons).replace(0, 1)
    
    # Calcular todas las columnas a la vez
    df['avg_price_average_std'] = df['avg_price_average'] / denominator
    df['max_price_high_std'] = df['max_price_high'] / denominator
    df['min_price_low_std'] = df['min_price_low'] / denominator
    
    logging.info(f"✓ Precios estandarizados: {len(df):,} registros")
    
    return df


def calculate_price_std_from_params(price_raw, nights, number_of_rooms, number_of_adults, number_of_kids):
    """
    Calcula precio estandarizado desde parámetros individuales.
    Formula: price / (nights * rooms * (adults + kids))
    Útil para la app.
    
    Args:
        price_raw: Precio total
        nights, number_of_rooms, number_of_adults, number_of_kids: Parámetros
    
    Returns:
        float: Precio estandarizado (precio por room-night-person)
    """
    # Cálculo optimizado sin logging por performance
    pseudo_row = pd.Series({
        'nights': nights,
        'number_of_rooms': number_of_rooms,
        'number_of_adults': number_of_adults,
        'number_of_kids': number_of_kids,
        'price': price_raw
    })
    
    return calculate_price_std(pseudo_row, 'price')


# ========================================
# TEMPORAL EXPANSION
# ========================================

def expand_dates_single_row(row):
    """
    Expands date range into daily observations.
    
    Converts a single row with date_start/date_end into multiple rows,
    one for each day in the range.
    
    Args:
        row (pd.Series): Row with 'date_start' and 'date_end' columns
    
    Returns:
        pd.DataFrame: DataFrame with one row per day in the date range
    """
    rango_fechas = pd.date_range(start=row['date_start'], end=row['date_end'])
    temp_df = pd.DataFrame([row] * len(rango_fechas))
    temp_df['date'] = rango_fechas
    return temp_df


def expand_dates_dataframe(df):
    """
    Aplica expansión temporal a todo el DataFrame.
    Versión ULTRA-OPTIMIZADA: usa numpy en lugar de iterrows (1000x más rápido).
    
    Args:
        df: DataFrame con 'date_start' y 'date_end'
    
    Returns:
        DataFrame expandido con columna 'date'
    """
    df = df.copy()
    df['date_start'] = pd.to_datetime(df['date_start'])
    df['date_end'] = pd.to_datetime(df['date_end'])
    
    logging.info(f"Expandiendo {len(df):,} registros a días (versión optimizada)...")
    
    # Calcular número de días por registro
    df['n_days'] = (df['date_end'] - df['date_start']).dt.days + 1
    
    # Crear índices repetidos
    repeat_counts = df['n_days'].values
    expanded_indices = np.repeat(df.index.values, repeat_counts)
    
    # Expandir DataFrame completo de una vez
    df_expanded = df.loc[expanded_indices].copy()
    
    # Calcular offsets de días para cada registro
    offsets = np.concatenate([np.arange(n) for n in repeat_counts])
    
    # Asignar fechas expandidas
    df_expanded['date'] = df_expanded['date_start'].values + pd.to_timedelta(offsets, unit='D')
    
    # Limpiar columna temporal
    df_expanded = df_expanded.drop(columns=['n_days'])
    
    logging.info(f"✓ Expansión: {len(df):,} → {len(df_expanded):,} observaciones diarias")
    
    return df_expanded


# ========================================
# FEATURE ENGINEERING
# ========================================

def get_week_in_month(day):
    """Retorna semana del mes (1-4)."""
    return config.get_week_in_month(day)


def add_temporal_features(df, date_column='date'):
    """
    Agrega features temporales.
    Versión optimizada: usa numpy para cálculo de semana.
    
    Args:
        df: DataFrame con columna de fecha
        date_column: Nombre de columna de fecha
    
    Returns:
        DataFrame con month, week_in_month
    """
    df = df.copy()
    df[date_column] = pd.to_datetime(df[date_column])
    
    df['month'] = df[date_column].dt.month
    df['day_of_month'] = df[date_column].dt.day
    
    # Vectorizar cálculo de semana del mes (más rápido que apply)
    days = df['day_of_month'].values
    week_in_month = np.ones(len(days), dtype=int)
    week_in_month[(days >= 8) & (days <= 15)] = 2
    week_in_month[(days >= 16) & (days <= 22)] = 3
    week_in_month[days >= 23] = 4
    
    df['week_in_month'] = week_in_month
    
    logging.info(f"Features temporales generadas: month, week_in_month")
    
    return df


# ========================================
# BASELINE CALCULATION
# ========================================

def media_ponderada(grupo_col, grupo_weight):
    """
    Calcula media ponderada por demanda (count_repeated).
    Versión optimizada que recibe Series directamente.
    
    Args:
        grupo_col: Series con valores a ponderar
        grupo_weight: Series con pesos (count_repeated)
    
    Returns:
        float: Media ponderada
    """
    total_ponderado = (grupo_col * grupo_weight).sum()
    total_peso = grupo_weight.sum()
    
    return total_ponderado / total_peso if total_peso > 0 else np.nan


def calculate_baselines(df, group_by_cols=None, enable_buckets=None):
    """
    Calcula baselines históricos por contexto (opcionalmente con buckets).
    
    Args:
        df: DataFrame expandido y estandarizado
        group_by_cols: Columnas de agrupación (opcional, sobrescribe enable_buckets)
        enable_buckets: Si True, incluye price_bucket en agrupación (default: config.ENABLE_PRICE_BUCKETS)
    
    Returns:
        DataFrame con baselines
    """
    # Determinar columnas de agrupación
    if group_by_cols is None:
        if enable_buckets is None:
            enable_buckets = config.ENABLE_PRICE_BUCKETS
        
        if enable_buckets:
            if 'price_bucket' not in df.columns:
                raise ValueError("enable_buckets=True pero falta columna 'price_bucket'")
            group_by_cols = ['destination_final', 'month', 'week_in_month', 'price_bucket']
        else:
            group_by_cols = ['destination_final', 'month', 'week_in_month']
    
    logging.info("=" * 60)
    logging.info("CALCULANDO BASELINES")
    logging.info("=" * 60)
    logging.info(f"Agrupación por: {group_by_cols}")
    
    # Optimización: hacer el groupby una sola vez y usar operaciones vectorizadas
    grouped = df.groupby(group_by_cols, dropna=False)
    
    # Calcular operaciones sencillas primero
    baselines = grouped.agg({
        'avg_price_average_std': ['std', 'count'],
        'min_price_low_std': 'min',
        'max_price_high_std': 'max',
        'count_repeated': 'sum',
        'destination_name': 'first'
    }).reset_index()
    
    # Aplanar columnas multinivel
    baselines.columns = list(group_by_cols) + ['std_price_std', 'price_count', 'min_price_std', 'max_price_std', 'count_obs', 'destination_name']
    
    # Calcular media ponderada de forma optimizada
    # En lugar de llamar media_ponderada por cada grupo, calculamos directamente
    weighted_means = []
    for name, group in grouped:
        weighted_mean = (group['avg_price_average_std'] * group['count_repeated']).sum() / group['count_repeated'].sum()
        weighted_means.append(weighted_mean)
    
    baselines['mean_price_std'] = weighted_means
    
    # Reordenar columnas
    baselines = baselines[list(group_by_cols) + ['mean_price_std', 'std_price_std', 'min_price_std', 'max_price_std', 'count_obs', 'destination_name']]
    
    logging.info(f"✓ Baselines calculados: {len(baselines):,} contextos")
    logging.info(f"  Destinos únicos: {baselines['destination_final'].nunique()}")
    logging.info(f"  Meses cubiertos: {sorted(baselines['month'].unique())}")
    
    if 'price_bucket' in baselines.columns:
        logging.info(f"  Buckets cubiertos: {sorted(baselines['price_bucket'].unique())}")
        logging.info(f"  Distribución de contextos por bucket:")
        for bucket in ['low', 'medium', 'high']:
            count = len(baselines[baselines['price_bucket'] == bucket])
            pct = (count / len(baselines) * 100) if len(baselines) > 0 else 0
            logging.info(f"    {bucket:8s}: {count:5,} contextos ({pct:5.1f}%)")
    
    return baselines


def apply_robustness_checks(baselines):
    """
    Aplica validaciones de robustez.
    
    Args:
        baselines: DataFrame con baselines
    
    Returns:
        DataFrame validado
    """
    baselines = baselines.copy()
    
    # Flag de baja confianza
    baselines['low_confidence'] = baselines['count_obs'] < config.MIN_OBSERVATIONS
    
    # Ajustar std muy bajas
    if config.USE_DYNAMIC_MIN_STD:
        baselines['min_std_threshold'] = baselines['mean_price_std'] * config.DYNAMIC_MIN_STD_PERCENT
        baselines['std_price_std'] = baselines.apply(
            lambda row: max(row['std_price_std'], row['min_std_threshold']) if pd.notna(row['std_price_std']) else row['min_std_threshold'],
            axis=1
        )
        baselines = baselines.drop(columns=['min_std_threshold'])
    else:
        baselines['std_price_std'] = baselines['std_price_std'].apply(
            lambda x: max(x, config.MIN_STD_PRICE) if pd.notna(x) else config.MIN_STD_PRICE
        )
    
    # Rellenar NaN
    baselines['std_price_std'] = baselines['std_price_std'].fillna(config.MIN_STD_PRICE)
    baselines = baselines.dropna(subset=['mean_price_std'])
    
    low_conf_count = baselines['low_confidence'].sum()
    logging.info(f"Validaciones aplicadas. Baselines finales: {len(baselines):,}")
    logging.warning(f"  Contextos con baja confianza: {low_conf_count:,} ({low_conf_count/len(baselines)*100:.1f}%)")
    logging.debug(f"  MIN_OBSERVATIONS usado: {config.MIN_OBSERVATIONS}")
    
    return baselines


# ========================================
# PRICE DISTRIBUTION & BUCKET CLASSIFICATION
# ========================================

def calculate_price_distribution_by_destination(df):
    """
    Calcula distribución de precios estandarizados por destino.
    
    Args:
        df: DataFrame con columnas:
            - destination_final
            - destination_name
            - avg_price_average_std (precio estandarizado)
    
    Returns:
        DataFrame con percentiles por destino
    """
    logging.info("=" * 60)
    logging.info("CALCULANDO DISTRIBUCIÓN DE PRECIOS POR DESTINO")
    logging.info("=" * 60)
    
    # Validar columna necesaria
    if 'avg_price_average_std' not in df.columns:
        raise ValueError("Falta columna 'avg_price_average_std'. Ejecutar standardize_prices primero.")
    
    # Agrupar por destino y calcular percentiles (optimizado con quantile)
    grouped = df.groupby(['destination_final', 'destination_name'])['avg_price_average_std']
    
    # Calcular todo en una sola pasada
    price_dist = grouped.agg(['count', 'min', 'mean', 'max']).reset_index()
    price_dist.columns = ['destination_final', 'destination_name', 'n_observations', 'min_price', 'mean_price', 'max_price']
    
    # Calcular percentiles (más rápido que múltiples quantile separados)
    percentiles_df = grouped.quantile([0.10, 0.25, 0.50, 0.75, 0.90]).unstack()
    percentiles_df.columns = ['p10', 'p25', 'p50', 'p75', 'p90']
    percentiles_df = percentiles_df.reset_index()
    
    # Merge de los dos resultados
    price_dist = price_dist.merge(percentiles_df, on=['destination_final', 'destination_name'])
    
    # Logging detallado
    logging.info(f"✓ Distribuciones calculadas para {len(price_dist)} destinos")
    logging.info(f"  Rango global de precios: ${price_dist['min_price'].min():.2f} - ${price_dist['max_price'].max():.2f}")
    logging.info(f"  Mediana global: ${price_dist['p50'].median():.2f}")
    
    # Mostrar top 5 destinos más caros
    top5 = price_dist.nlargest(5, 'p50')[['destination_name', 'p50']]
    logging.debug("  Top 5 destinos más caros (mediana):")
    for _, row in top5.iterrows():
        logging.debug(f"    {row['destination_name']:30s}: ${row['p50']:.2f}")
    
    return price_dist


def classify_observations_into_buckets(df, price_dist):
    """
    Clasifica cada observación en bucket de precio (low/medium/high).
    Versión optimizada con operaciones numpy.
    
    Args:
        df: DataFrame con observaciones históricas
        price_dist: DataFrame con percentiles por destino
    
    Returns:
        DataFrame con columna 'price_bucket'
    """
    logging.info("=" * 60)
    logging.info("CLASIFICANDO OBSERVACIONES EN BUCKETS")
    logging.info("=" * 60)
    
    # Merge con thresholds (copy=False para evitar copia innecesaria)
    df = df.merge(
        price_dist[['destination_final', 'p25', 'p50', 'p75']],
        on='destination_final',
        how='left',
        copy=False
    )
    
    # Usar numpy arrays para clasificación (más rápido)
    price = df['avg_price_average_std'].values
    p25 = df['p25'].values
    p75 = df['p75'].values
    p50 = df['p50'].values
    
    # Inicializar con medium por defecto
    bucket = np.full(len(df), 'medium', dtype='object')
    
    # Máscaras booleanas
    valid = ~(np.isnan(price) | np.isnan(p25) | np.isnan(p75))
    bucket[valid & (price <= p25)] = 'low'
    bucket[valid & (price >= p75)] = 'high'
    bucket[~valid] = np.nan
    
    df['price_bucket'] = bucket
    
    # Calcular RPI vectorizado
    df['relative_price_index'] = np.where(p50 > 0, price / p50, np.nan)
    
    # Limpiar columnas temporales
    df.drop(columns=['p25', 'p50', 'p75'], inplace=True)
    
    # Estadísticas
    total = len(df)
    unique_buckets, counts = np.unique(bucket[~pd.isna(bucket)], return_counts=True)
    
    logging.info(f"✓ Clasificación completada: {total:,} observaciones")
    logging.info(f"  Distribución de buckets:")
    for b, c in zip(unique_buckets, counts):
        pct = (c / total * 100) if total > 0 else 0
        logging.info(f"    {b:8s}: {c:8,} ({pct:5.1f}%)")
    
    # Remover observaciones sin bucket
    df_filtered = df[df['price_bucket'].notna()].copy()
    removed = len(df) - len(df_filtered)
    if removed > 0:
        logging.info(f"  Removidas {removed:,} observaciones sin bucket")
    
    return df_filtered


def generate_bucket_summary(baselines):
    """
    Genera resumen de cobertura de buckets.
    
    Args:
        baselines: DataFrame con baselines por bucket
    
    Returns:
        DataFrame con resumen de cobertura
    """
    if 'price_bucket' not in baselines.columns:
        logging.warning("No hay columna price_bucket, saltando bucket_summary")
        return None
    
    summary = baselines.groupby(['destination_final', 'destination_name', 'price_bucket']).agg(
        n_contexts=('mean_price_std', 'count'),
        total_observations=('count_obs', 'sum'),
        avg_observations_per_context=('count_obs', 'mean'),
        high_confidence_pct=('low_confidence', lambda x: (~x).sum() / len(x) * 100 if len(x) > 0 else 0)
    ).reset_index()
    
    logging.info(f"✓ Bucket summary generado: {len(summary)} entradas")
    
    return summary


# ========================================
# DEAL SCORING
# ========================================

def calculate_relative_score(hotel_price_std, mean_price_std, std_price_std):
    """
    Calcula z-score.
    
    Args:
        hotel_price_std: Precio del hotel
        mean_price_std: Media del baseline
        std_price_std: Desv. estándar del baseline
    
    Returns:
        float: Z-score
    """
    if std_price_std == 0 or pd.isna(std_price_std):
        std_price_std = mean_price_std * 0.10
    
    return (hotel_price_std - mean_price_std) / std_price_std


def classify_deal(z_score):
    """
    Clasifica precio según z-score.
    
    Args:
        z_score: Relative score
    
    Returns:
        str: Clasificación
    """
    if pd.isna(z_score):
        return config.CLASSIFICATION_LABELS['insufficient_data']
    
    if z_score < config.THRESHOLDS['deal']:
        return config.CLASSIFICATION_LABELS['deal']
    elif z_score < config.THRESHOLDS['good_price']:
        return config.CLASSIFICATION_LABELS['good_price']
    elif z_score <= config.THRESHOLDS['normal_upper']:
        return config.CLASSIFICATION_LABELS['normal']
    else:
        return config.CLASSIFICATION_LABELS['expensive']


def is_deal(z_score):
    """Retorna True si es deal."""
    return z_score < config.THRESHOLDS['deal'] if not pd.isna(z_score) else False


def calculate_percentile(z_score):
    """Calcula percentil asumiendo distribución normal."""
    return stats.norm.cdf(z_score) * 100 if not pd.isna(z_score) else None


def get_baseline_for_context(baselines, destination, month, week_in_month):
    """
    Busca baseline para un contexto específico.
    
    Args:
        baselines: DataFrame con baselines
        destination, month, week_in_month: Contexto
    
    Returns:
        dict o None
    """
    result = baselines[
        (baselines['destination_final'] == destination) &
        (baselines['month'] == month) &
        (baselines['week_in_month'] == week_in_month)
    ]
    
    return result.iloc[0].to_dict() if len(result) > 0 else None


# ========================================
# SAVE/LOAD
# ========================================

def save_baselines(baselines, output_path=None):
    """
    Guarda baselines en CSV.
    
    Args:
        baselines: DataFrame
        output_path: Path de salida (default: config.BASELINES_FILE)
    """
    if output_path is None:
        output_path = config.BASELINES_FILE
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    baselines.to_csv(output_path, index=False)
    logging.info(f"Baselines guardados: {output_path}")
    logging.debug(f"  Tamaño: {output_path.stat().st_size / 1024:.1f} KB")
    logging.debug(f"  Registros: {len(baselines):,}")


def load_baselines(baselines_path=None):
    """
    Carga baselines desde CSV.
    
    Args:
        baselines_path: Path (default: config.BASELINES_FILE)
    
    Returns:
        DataFrame
    """
    if baselines_path is None:
        baselines_path = config.BASELINES_FILE
    
    baselines_path = Path(baselines_path)
    
    if not baselines_path.exists():
        raise FileNotFoundError(f"Baselines no encontrado: {baselines_path}")
    
    baselines = pd.read_csv(baselines_path)
    logging.info(f"Baselines cargados: {len(baselines):,} contextos")
    logging.debug(f"  Destinos: {baselines['destination_final'].nunique()}")
    logging.debug(f"  Alta confianza: {(~baselines['low_confidence']).sum():,}")
    
    return baselines
