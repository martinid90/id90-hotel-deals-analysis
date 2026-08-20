# auxiliary_functions.py
# Funciones auxiliares para el sistema de detección de deals hoteleros
# Implementa mejoras en mapeo jerárquico, cálculo robusto de baselines con fallbacks y estadísticas ponderadas.

import pandas as pd
import numpy as np
from scipy import stats
import glob
import re
import unicodedata
from pathlib import Path
import logging
import config

# Configurar logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format=config.LOG_FORMAT
)


# ========================================
# STRING NORMALIZATION & TEXT UTILITIES
# ========================================

def strip_accents(text):
    """
    Normaliza texto removiendo acentos/diacríticos, espacios extras y pasando a minúsculas.
    
    Args:
        text (str): Texto de entrada
        
    Returns:
        str: Texto normalizado en minúsculas y sin acentos
    """
    if pd.isna(text) or not isinstance(text, str):
        return ""
    # Descomposición canónica (NFD) y filtrado de marcas diacríticas
    normalized = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    # Limpiar espacios múltiples y pasar a minúsculas
    cleaned = re.sub(r"\s+", " ", normalized).strip().casefold()
    return cleaned


# Diccionario canónico de estados de EE.UU. (nombres completos -> códigos de 2 letras)
US_STATE_CODES = {
    'alabama': 'al', 'alaska': 'ak', 'arizona': 'az', 'arkansas': 'ar', 'california': 'ca',
    'colorado': 'co', 'connecticut': 'ct', 'delaware': 'de', 'florida': 'fl', 'georgia': 'ga',
    'hawaii': 'hi', 'idaho': 'id', 'illinois': 'il', 'indiana': 'in', 'iowa': 'ia',
    'kansas': 'ks', 'kentucky': 'ky', 'louisiana': 'la', 'maine': 'me', 'maryland': 'md',
    'massachusetts': 'ma', 'michigan': 'mi', 'minnesota': 'mn', 'mississippi': 'ms', 'missouri': 'mo',
    'montana': 'mt', 'nebraska': 'ne', 'nevada': 'nv', 'new hampshire': 'nh', 'new jersey': 'nj',
    'new mexico': 'nm', 'new york': 'ny', 'north carolina': 'nc', 'north dakota': 'nd', 'ohio': 'oh',
    'oklahoma': 'ok', 'oregon': 'or', 'pennsylvania': 'pa', 'rhode island': 'ri', 'south carolina': 'sc',
    'south dakota': 'sd', 'tennessee': 'tn', 'texas': 'tx', 'utah': 'ut', 'vermont': 'vt',
    'virginia': 'va', 'washington': 'wa', 'west virginia': 'wv', 'wisconsin': 'wi', 'wyoming': 'wy',
    'district of columbia': 'dc', 'puerto rico': 'pr', 'guam': 'gu', 'virgin islands': 'vi'
}


# ========================================
# DATA LOADING
# ========================================

def load_all_historicals(data_path=None):
    """
    Carga todos los archivos históricos CSV desde el directorio especificado.
    
    Args:
        data_path (Path, optional): Ruta al directorio (default: config.PRICE_HISTORICALS_DIR)
    
    Returns:
        pd.DataFrame: DataFrame combinado con todos los registros históricos
    
    Raises:
        FileNotFoundError: Si no se encuentran archivos CSV en el directorio
    """
    if data_path is None:
        data_path = config.PRICE_HISTORICALS_DIR
    
    data_path = Path(data_path)
    pattern = str(data_path / config.HISTORICALS_FILE_PATTERN)
    historical_files = [Path(f) for f in glob.glob(pattern)]
    
    if not historical_files:
        raise FileNotFoundError(f"No se encontraron archivos en {data_path} con el patrón {config.HISTORICALS_FILE_PATTERN}")
    
    logging.info(f"Cargando {len(historical_files)} archivos históricos...")
    
    dfs = []
    for file in historical_files:
        df_temp = pd.read_csv(
            file,
            dtype={'city': str, 'state': str, 'country': str, 'country_code': str},
            low_memory=False
        )
        df_temp['source_file'] = file.name
        dfs.append(df_temp)
        logging.info(f"  ✓ {file.name}: {len(df_temp):,} registros")
    
    df_combined = pd.concat(dfs, ignore_index=True)
    logging.info(f"Total cargado: {len(df_combined):,} registros")
    
    return df_combined


def load_destination_mapping(mapping_path=None):
    """
    Carga el archivo de mapping de destinos geográficos.
    
    Args:
        mapping_path: Ruta al archivo (usa config por defecto)
        
    Returns:
        pd.DataFrame con el mapping
    """
    if mapping_path is None:
        mapping_path = config.DESTINATION_MAPPING_FILE
    
    mapping_path = Path(mapping_path)
    if not mapping_path.exists():
        logging.warning(f"Archivo de mapping no encontrado: {mapping_path}")
        return pd.DataFrame()
    
    mapping_df = pd.read_csv(
        mapping_path,
        dtype={'nearest_destination_id': str, 'city': str, 'state': str, 'country': str, 'country_code': str},
        low_memory=False
    )
    logging.info(f"Mapping cargado: {len(mapping_df):,} registros")
    logging.info(f"  Destinos canónicos únicos: {mapping_df['nearest_destination_id'].nunique():,}")
    
    return mapping_df


def validate_data(df):
    """
    Filtra registros inválidos y outliers extremos:
    - Denominadores inválidos: nights <= 0, rooms <= 0, (adults + kids) <= 0
    - Precios no válidos o extremos (<= 0 o > $50,000 por errores de scraping/monedas no USD)
    
    Args:
        df (pd.DataFrame): DataFrame con datos históricos
        
    Returns:
        pd.DataFrame: DataFrame filtrado con registros válidos
    """
    initial_count = len(df)
    
    # 1. Filtro de denominadores válidos
    valid_mask = (
        (df['nights'] > 0) & 
        (df['number_of_rooms'] > 0) & 
        ((df['number_of_adults'] + df['number_of_kids']) > 0)
    )
    
    # 2. Filtro de precios válidos (si la columna existe)
    if 'avg_price_average' in df.columns:
        valid_mask = valid_mask & (df['avg_price_average'] > 0) & (df['avg_price_average'] <= 50000)
    
    valid_df = df[valid_mask].copy()
    removed_count = initial_count - len(valid_df)
    
    if removed_count > 0:
        logging.warning(f"Registros eliminados por datos inválidos u outliers extremos: {removed_count:,} ({100*removed_count/initial_count:.2f}%)")
    else:
        logging.info("✓ Todos los registros son válidos")
    
    logging.info(f"Registros válidos: {len(valid_df):,} ({100*len(valid_df)/initial_count:.1f}%)")
    
    return valid_df


# ========================================
# HIERARCHICAL WATERFALL DESTINATION MAPPING
# ========================================

def apply_destination_mapping(df, mapping_df):
    """
    Aplica mapping jerárquico en cascada (Waterfall Matching) para maximizar la cobertura:
    1. Coincidencia exacta país + código de estado + ciudad (ej. 'US - FL - Orlando')
    2. Coincidencia país + nombre completo de estado + ciudad (ej. 'US - Florida - Orlando')
    3. Coincidencia país + ciudad (ej. 'DO - Bavaro', 'AR - Buenos Aires')
    4. Coincidencia por tupla (país, ciudad) en el catálogo de ciudades
    5. Fallback a ciudad cruda si no se encuentra en el mapping.
    
    Args:
        df: DataFrame con columnas 'country_code', 'state', 'city'
        mapping_df: DataFrame con 'reference', 'city', 'nearest_destination_id', 'nearest_destination_name'
        
    Returns:
        DataFrame con:
        - 'nearest_destination_id', 'nearest_destination_name'
        - 'destination_final', 'destination_name'
        - 'is_mapped' (bool): True si mapeó a un destino canónico
    """
    if mapping_df is None or len(mapping_df) == 0:
        logging.warning("No hay mapping disponible, usando 'city' como destino")
        df = df.copy()
        df['destination_final'] = df['city']
        df['destination_name'] = df['city']
        df['is_mapped'] = False
        df['nearest_destination_id'] = np.nan
        df['nearest_destination_name'] = np.nan
        return df

    df = df.copy()
    
    # 1. Normalizar catálogo de mapping
    map_clean = mapping_df.copy()
    map_clean['ref_clean'] = map_clean['reference'].astype(str).apply(strip_accents)
    map_clean['city_clean'] = map_clean['city'].astype(str).apply(strip_accents)
    map_clean['country_clean'] = map_clean['ref_clean'].str.split(' - ').str[0].str.strip()
    
    # Diccionarios de búsqueda rápida
    ref_to_id = map_clean.drop_duplicates('ref_clean').set_index('ref_clean')['nearest_destination_id'].to_dict()
    ref_to_name = map_clean.drop_duplicates('ref_clean').set_index('ref_clean')['nearest_destination_name'].to_dict()
    
    country_city_to_id = map_clean.drop_duplicates(['country_clean', 'city_clean']).set_index(['country_clean', 'city_clean'])['nearest_destination_id'].to_dict()
    country_city_to_name = map_clean.drop_duplicates(['country_clean', 'city_clean']).set_index(['country_clean', 'city_clean'])['nearest_destination_name'].to_dict()

    # 2. Extraer combinaciones geográficas únicas de los datos de entrada para optimizar performance
    geo = df[['country_code', 'state', 'city']].drop_duplicates().copy()
    geo['country_clean'] = geo['country_code'].astype(str).apply(strip_accents)
    geo['state_clean'] = geo['state'].astype(str).apply(strip_accents)
    geo['city_clean'] = geo['city'].astype(str).apply(strip_accents)
    
    # Mapear estado a código de 2 letras (ej. 'Florida' -> 'fl')
    geo['state_code'] = geo['state_clean'].map(US_STATE_CODES).fillna(geo['state_clean'])

    # Construir claves de búsqueda
    k_state_code = geo['country_clean'] + ' - ' + geo['state_code'] + ' - ' + geo['city_clean']
    k_state_name = geo['country_clean'] + ' - ' + geo['state_clean'] + ' - ' + geo['city_clean']
    k_country_city = geo['country_clean'] + ' - ' + geo['city_clean']

    # Cascada de matching:
    # Nivel 1: país - código de estado - ciudad
    m_id = k_state_code.map(ref_to_id)
    m_name = k_state_code.map(ref_to_name)

    # Nivel 2: país - nombre de estado - ciudad
    m_id = m_id.combine_first(k_state_name.map(ref_to_id))
    m_name = m_name.combine_first(k_state_name.map(ref_to_name))

    # Nivel 3: país - ciudad
    m_id = m_id.combine_first(k_country_city.map(ref_to_id))
    m_name = m_name.combine_first(k_country_city.map(ref_to_name))

    # Nivel 4: Tupla (país, ciudad) en catálogo
    cc_idx = pd.MultiIndex.from_arrays([geo['country_clean'], geo['city_clean']])
    m_id = m_id.combine_first(pd.Series(cc_idx.map(country_city_to_id), index=geo.index))
    m_name = m_name.combine_first(pd.Series(cc_idx.map(country_city_to_name), index=geo.index))

    geo['nearest_destination_id'] = m_id
    geo['nearest_destination_name'] = m_name

    # 3. Merge eficiente de vuelta al DataFrame principal
    geo_mapping = geo[['country_code', 'state', 'city', 'nearest_destination_id', 'nearest_destination_name']]
    
    # Limpiar columnas previas si existían
    cols_to_drop = [c for c in ['nearest_destination_id', 'nearest_destination_name', 'destination_final', 'destination_name', 'is_mapped'] if c in df.columns]
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)

    df = df.merge(geo_mapping, on=['country_code', 'state', 'city'], how='left')

    # Flag real de mapeo
    df['is_mapped'] = df['nearest_destination_id'].notna()

    # Asignar destination_final y destination_name (con fallback limpio a city)
    df['destination_final'] = df['nearest_destination_id'].fillna(df['city'])
    df['destination_name'] = df['nearest_destination_name'].fillna(df['city'])

    matched = int(df['is_mapped'].sum())
    total = len(df)
    pct = (matched / total * 100) if total > 0 else 0
    
    logging.info(f"✓ Mapping jerárquico aplicado: {matched:,}/{total:,} registros ({pct:.1f}%)")
    logging.info(f"  Destinos únicos finales: {df['destination_final'].nunique():,}")

    return df


# Alias para retrocompatibilidad
apply_destination_mapping_REVISADO = apply_destination_mapping


# ========================================
# PRICE STANDARDIZATION
# ========================================

def calculate_price_std(row, col_name):
    """
    Calcula precio estandarizado para una fila.
    Fórmula: price / (nights * rooms * (adults + kids))
    
    Args:
        row: pd.Series con nights, number_of_rooms, number_of_adults, number_of_kids
        col_name: Nombre de la columna de precio
        
    Returns:
        float: Precio estandarizado
    """
    rules = config.STANDARDIZATION_RULES
    
    nights = row['nights'] if row['nights'] >= rules['nights']['threshold'] else rules['nights']['fallback']
    rooms = row['number_of_rooms'] if row['number_of_rooms'] >= rules['number_of_rooms']['threshold'] else rules['number_of_rooms']['fallback']
    adults = row['number_of_adults'] if row['number_of_adults'] >= rules['number_of_adults']['threshold'] else rules['number_of_adults']['fallback']
    kids = row.get('number_of_kids', 0)
    if pd.isna(kids):
        kids = 0
    
    total_persons = adults + kids
    if total_persons == 0:
        total_persons = 1
    
    denominator = nights * rooms * total_persons
    if denominator == 0:
        denominator = 1
    
    return float(row[col_name]) / denominator


# Alias requerido por test_system.py
calcular_total_std = calculate_price_std


def standardize_prices(df):
    """
    Aplica estandarización vectorizada a las columnas de precio.
    
    Args:
        df: DataFrame con columnas crudas de precio
        
    Returns:
        DataFrame con columnas *_std
    """
    df = df.copy()
    rules = config.STANDARDIZATION_RULES
    
    nights = df['nights'].where(df['nights'] >= rules['nights']['threshold'], rules['nights']['fallback'])
    rooms = df['number_of_rooms'].where(df['number_of_rooms'] >= rules['number_of_rooms']['threshold'], rules['number_of_rooms']['fallback'])
    adults = df['number_of_adults'].where(df['number_of_adults'] >= rules['number_of_adults']['threshold'], rules['number_of_adults']['fallback'])
    kids = df['number_of_kids'].fillna(0)
    
    total_persons = (adults + kids).replace(0, 1)
    denominator = (nights * rooms * total_persons).replace(0, 1)
    
    if 'avg_price_average' in df.columns:
        df['avg_price_average_std'] = df['avg_price_average'] / denominator
    if 'max_price_high' in df.columns:
        df['max_price_high_std'] = df['max_price_high'] / denominator
    if 'min_price_low' in df.columns:
        df['min_price_low_std'] = df['min_price_low'] / denominator
        
    logging.info(f"✓ Precios estandarizados: {len(df):,} registros")
    return df


def calculate_price_std_from_params(price_raw, nights, number_of_rooms, number_of_adults, number_of_kids):
    """
    Calcula precio estandarizado a partir de parámetros individuales.
    Útil para la interfaz de usuario de Streamlit.
    """
    pseudo_row = pd.Series({
        'nights': nights,
        'number_of_rooms': number_of_rooms,
        'number_of_adults': number_of_adults,
        'number_of_kids': number_of_kids,
        'price': price_raw
    })
    return calculate_price_std(pseudo_row, 'price')


# ========================================
# TEMPORAL EXPANSION & FEATURES
# ========================================

def expand_dates_single_row(row):
    """Expande una fila a observaciones diarias."""
    rango_fechas = pd.date_range(start=row['date_start'], end=row['date_end'])
    temp_df = pd.DataFrame([row] * len(rango_fechas))
    temp_df['date'] = rango_fechas
    return temp_df


def expand_dates_dataframe(df):
    """
    Aplica expansión temporal vectorizada ultrarrápida a todo el DataFrame.
    """
    df = df.copy()
    df['date_start'] = pd.to_datetime(df['date_start'])
    df['date_end'] = pd.to_datetime(df['date_end'])
    
    logging.info(f"Expandiendo {len(df):,} registros a días...")
    
    df['n_days'] = (df['date_end'] - df['date_start']).dt.days + 1
    # Asegurar al menos 1 día
    df['n_days'] = df['n_days'].clip(lower=1)
    
    repeat_counts = df['n_days'].values
    expanded_indices = np.repeat(df.index.values, repeat_counts)
    
    df_expanded = df.loc[expanded_indices].copy()
    offsets = np.concatenate([np.arange(n) for n in repeat_counts])
    
    df_expanded['date'] = df_expanded['date_start'].values + pd.to_timedelta(offsets, unit='D')
    df_expanded = df_expanded.drop(columns=['n_days'])
    
    logging.info(f"✓ Expansión: {len(df):,} → {len(df_expanded):,} observaciones diarias")
    return df_expanded


def get_week_in_month(day):
    """Retorna la semana del mes (1-4)."""
    return config.get_week_in_month(day)


def add_temporal_features(df, date_column='date'):
    """
    Agrega features temporales (month, week_in_month, day_of_week, dow).
    """
    df = df.copy()
    df[date_column] = pd.to_datetime(df[date_column])
    
    df['month'] = df[date_column].dt.month
    df['day_of_month'] = df[date_column].dt.day
    df['day_of_week'] = df[date_column].dt.day_name()
    df['dow'] = df[date_column].dt.dayofweek
    
    days = df['day_of_month'].values
    week_in_month = np.ones(len(days), dtype=int)
    week_in_month[(days >= 8) & (days <= 15)] = 2
    week_in_month[(days >= 16) & (days <= 22)] = 3
    week_in_month[days >= 23] = 4
    
    df['week_in_month'] = week_in_month
    
    logging.info("✓ Features temporales generadas: month, week_in_month, dow")
    return df


# ========================================
# PRICE DISTRIBUTION & BUCKETS
# ========================================

def calculate_price_distribution_by_destination(df):
    """
    Calcula distribución de precios estandarizados y percentiles por destino.
    """
    logging.info("=" * 60)
    logging.info("CALCULANDO DISTRIBUCIÓN DE PRECIOS POR DESTINO")
    logging.info("=" * 60)
    
    if 'avg_price_average_std' not in df.columns:
        raise ValueError("Falta columna 'avg_price_average_std'. Ejecutar standardize_prices primero.")
    
    # Filtrar precios válidos y no outliers
    valid_df = df[
        (df['avg_price_average_std'].notna()) & 
        (df['avg_price_average_std'] > 0) & 
        (df['avg_price_average_std'] < 2000)
    ]
    
    grouped = valid_df.groupby(['destination_final', 'destination_name'])['avg_price_average_std']
    
    price_dist = grouped.agg(
        n_observations='count',
        min_price='min',
        mean_price='mean',
        max_price='max'
    ).reset_index()
    
    percentiles_df = grouped.quantile([0.10, 0.25, 0.50, 0.75, 0.90]).unstack()
    percentiles_df.columns = ['p10', 'p25', 'p50', 'p75', 'p90']
    percentiles_df = percentiles_df.reset_index()
    
    price_dist = price_dist.merge(percentiles_df, on=['destination_final', 'destination_name'])
    
    logging.info(f"✓ Distribuciones calculadas para {len(price_dist):,} destinos")
    return price_dist


def classify_observations_into_buckets(df, price_dist):
    """
    Clasifica observaciones en buckets de precio ('low'=Budget, 'medium'=Mid-Range, 'high'=Premium).
    """
    logging.info("=" * 60)
    logging.info("CLASIFICANDO OBSERVACIONES EN BUCKETS")
    logging.info("=" * 60)
    
    df = df.merge(
        price_dist[['destination_final', 'p25', 'p50', 'p75']],
        on='destination_final',
        how='left'
    )
    
    price = df['avg_price_average_std'].values
    p25 = df['p25'].values
    p75 = df['p75'].values
    p50 = df['p50'].values
    
    bucket = np.full(len(df), 'medium', dtype='object')
    valid = ~(np.isnan(price) | np.isnan(p25) | np.isnan(p75))
    bucket[valid & (price <= p25)] = 'low'
    bucket[valid & (price >= p75)] = 'high'
    bucket[~valid] = np.nan
    
    df['price_bucket'] = bucket
    df['relative_price_index'] = np.where(p50 > 0, price / p50, np.nan)
    df.drop(columns=['p25', 'p50', 'p75'], inplace=True)
    
    df_filtered = df[df['price_bucket'].notna()].copy()
    logging.info(f"✓ Clasificación completada: {len(df_filtered):,} observaciones con bucket asignado")
    
    return df_filtered


def generate_bucket_summary(baselines):
    """Genera resumen estadístico de cobertura de buckets."""
    if 'price_bucket' not in baselines.columns:
        return None
    
    summary = baselines.groupby(['destination_final', 'destination_name', 'price_bucket']).agg(
        n_contexts=('mean_price_std', 'count'),
        total_observations=('count_obs', 'sum'),
        avg_observations_per_context=('count_obs', 'mean'),
        high_confidence_pct=('low_confidence', lambda x: (~x).sum() / len(x) * 100 if len(x) > 0 else 0)
    ).reset_index()
    
    return summary


# ========================================
# ROBUST BASELINES WITH WEIGHTED STATISTICS
# ========================================

def media_ponderada(grupo_col, grupo_weight):
    """Calcula media ponderada por demanda."""
    total_ponderado = (grupo_col * grupo_weight).sum()
    total_peso = grupo_weight.sum()
    return total_ponderado / total_peso if total_peso > 0 else np.nan


def calculate_baselines(df, group_by_cols=None, enable_buckets=None):
    """
    Calcula baselines históricos por contexto aplicando media y desvío estándar ponderados.
    
    Args:
        df: DataFrame estandarizado y expandido
        group_by_cols: Columnas de contexto
        enable_buckets: Si True, incluye price_bucket
        
    Returns:
        DataFrame con baselines estadísticos
    """
    if group_by_cols is None:
        if enable_buckets is None:
            enable_buckets = config.ENABLE_PRICE_BUCKETS
        
        if enable_buckets and 'price_bucket' in df.columns:
            group_by_cols = ['destination_final', 'month', 'week_in_month', 'price_bucket']
        else:
            group_by_cols = ['destination_final', 'month', 'week_in_month']
    
    logging.info("=" * 60)
    logging.info(f"CALCULANDO BASELINES (Agrupación: {group_by_cols})")
    logging.info("=" * 60)
    
    # Preparar columnas
    df = df.copy()
    if 'count_repeated' not in df.columns:
        df['count_repeated'] = 1
    else:
        df['count_repeated'] = df['count_repeated'].fillna(1).clip(lower=1)
        
    if 'min_price_low_std' not in df.columns:
        df['min_price_low_std'] = df['avg_price_average_std']
    if 'max_price_high_std' not in df.columns:
        df['max_price_high_std'] = df['avg_price_average_std']

    # Precalcular ponderadores para cálculo vectorizado instantáneo
    df['wx'] = df['count_repeated'] * df['avg_price_average_std']
    df['wx2'] = df['count_repeated'] * (df['avg_price_average_std'] ** 2)

    # Agregación básica vectorizada
    grouped = df.groupby(group_by_cols, dropna=False)
    
    agg_dict = {
        'destination_name': 'first',
        'min_price_low_std': 'min',
        'max_price_high_std': 'max',
        'count_repeated': 'sum',
        'wx': 'sum',
        'wx2': 'sum',
        'avg_price_average_std': 'count'  # conteo de filas
    }
    
    baselines = grouped.agg(agg_dict).reset_index()
    
    # Cálculo vectorizado instantáneo de media y desvío ponderados
    w_sum = baselines['count_repeated'].values
    sum_wx = baselines['wx'].values
    sum_wx2 = baselines['wx2'].values
    
    mean_w = np.where(w_sum > 0, sum_wx / w_sum, np.nan)
    var_w = np.where(w_sum > 0, (sum_wx2 / w_sum) - (mean_w ** 2), np.nan)
    std_w = np.sqrt(np.maximum(var_w, 0.0))
    
    baselines['mean_price_std'] = mean_w
    baselines['std_price_std'] = std_w
    
    baselines.rename(columns={
        'min_price_low_std': 'min_price_std',
        'max_price_high_std': 'max_price_std',
        'count_repeated': 'count_obs',
        'avg_price_average_std': 'count_records'
    }, inplace=True)
    baselines.drop(columns=['wx', 'wx2'], inplace=True)
    
    logging.info(f"✓ Baselines calculados: {len(baselines):,} contextos")
    logging.info(f"  Destinos únicos: {baselines['destination_final'].nunique():,}")
    
    return baselines


def apply_robustness_checks(baselines):
    """
    Aplica verificaciones de robustez y pisos mínimos de variabilidad.
    """
    baselines = baselines.copy()
    
    # Flag de baja confianza (menos de MIN_OBSERVATIONS)
    baselines['low_confidence'] = baselines['count_obs'] < config.MIN_OBSERVATIONS
    
    # Ajustar desviaciones estándar mínimas
    if config.USE_DYNAMIC_MIN_STD:
        baselines['min_std_threshold'] = (baselines['mean_price_std'] * config.DYNAMIC_MIN_STD_PERCENT).clip(lower=5.0)
        baselines['std_price_std'] = baselines.apply(
            lambda row: max(row['std_price_std'], row['min_std_threshold']) if pd.notna(row['std_price_std']) else row['min_std_threshold'],
            axis=1
        )
        baselines = baselines.drop(columns=['min_std_threshold'])
    else:
        baselines['std_price_std'] = baselines['std_price_std'].apply(
            lambda x: max(x, config.MIN_STD_PRICE) if pd.notna(x) else config.MIN_STD_PRICE
        )
    
    baselines['std_price_std'] = baselines['std_price_std'].fillna(config.MIN_STD_PRICE)
    baselines = baselines.dropna(subset=['mean_price_std'])
    
    low_conf_count = baselines['low_confidence'].sum()
    logging.info(f"✓ Validaciones aplicadas. Baselines finales: {len(baselines):,}")
    logging.info(f"  Alta confianza: {(~baselines['low_confidence']).sum():,} ({100*(~baselines['low_confidence']).mean():.1f}%)")
    
    return baselines


# ========================================
# DEAL SCORING & CLASSIFICATION
# ========================================

def calculate_relative_score(hotel_price_std, mean_price_std, std_price_std):
    """Calcula Z-Score con salvaguarda contra división por cero."""
    if std_price_std == 0 or pd.isna(std_price_std):
        std_price_std = max(mean_price_std * 0.10, 5.0)
    return (hotel_price_std - mean_price_std) / std_price_std


def classify_deal(z_score):
    """Clasifica el precio según su Z-score."""
    if pd.isna(z_score):
        return config.CLASSIFICATION_LABELS.get('insufficient_data', 'Insufficient Data')
    
    if z_score < config.THRESHOLDS['deal']:
        return config.CLASSIFICATION_LABELS.get('deal', 'Deal')
    elif z_score < config.THRESHOLDS['good_price']:
        return config.CLASSIFICATION_LABELS.get('good_price', 'Good Price')
    elif z_score <= config.THRESHOLDS['normal_upper']:
        return config.CLASSIFICATION_LABELS.get('normal', 'Normal Price')
    else:
        return config.CLASSIFICATION_LABELS.get('expensive', 'Expensive')


def is_deal(z_score):
    """Retorna True si clasifica como deal."""
    return bool(z_score < config.THRESHOLDS['deal']) if not pd.isna(z_score) else False


def calculate_percentile(z_score):
    """Calcula percentil bajo distribución normal."""
    return float(stats.norm.cdf(z_score) * 100) if not pd.isna(z_score) else None


def get_baseline_for_context(baselines, destination, month, week_in_month):
    """Busca baseline para un contexto específico."""
    dest_str = re.sub(r'\.0$', '', str(destination))
    dest_col = baselines['destination_final'].astype(str).str.replace(r'\.0$', '', regex=True)
    result = baselines[
        (dest_col == dest_str) &
        (baselines['month'] == month) &
        (baselines['week_in_month'] == week_in_month)
    ]
    return result.iloc[0].to_dict() if len(result) > 0 else None


# ========================================
# HIERARCHICAL FALLBACK EVALUATION
# ========================================

def evaluate_hotel_price(destination_final, month, week_in_month, price_std, baselines_df):
    """
    Evalúa precio contra baselines aplicando búsqueda jerárquica con fallback para máxima confiabilidad.
    """
    dest_str = re.sub(r'\.0$', '', str(destination_final))
    dest_col = baselines_df['destination_final'].astype(str).str.replace(r'\.0$', '', regex=True)
    
    # 1. Búsqueda exacta: destino + mes + semana
    subset = baselines_df[
        (dest_col == dest_str) &
        (baselines_df['month'] == month) &
        (baselines_df['week_in_month'] == week_in_month)
    ]
    
    fallback_level = 'exact'
    
    # 2. Fallback mensual: destino + mes
    if subset.empty:
        subset = baselines_df[
            (dest_col == dest_str) &
            (baselines_df['month'] == month)
        ]
        fallback_level = 'month'
        
    # 3. Fallback anual: destino general
    if subset.empty:
        subset = baselines_df[dest_col == dest_str]
        fallback_level = 'destination_overall'
    
    if subset.empty:
        return {
            'classification': config.CLASSIFICATION_LABELS.get('insufficient_data', 'Sin datos'),
            'z_score': None,
            'baseline_info': None,
            'confidence': 'low',
            'used_fallback': True,
            'fallback_level': 'none'
        }
    
    baseline = subset.iloc[0]
    mean_val = float(baseline['mean_price_std'])
    std_val = float(baseline['std_price_std'])
    if std_val == 0 or pd.isna(std_val):
        std_val = max(mean_val * 0.10, 5.0)
        
    z_score = (price_std - mean_val) / std_val
    classification = classify_deal(z_score)
    
    confidence = 'high' if (not baseline.get('low_confidence', False) and fallback_level == 'exact') else ('medium' if fallback_level != 'destination_overall' else 'low')
    
    return {
        'classification': classification,
        'z_score': float(z_score),
        'baseline_info': {
            'mean': mean_val,
            'std': std_val,
            'count': int(baseline.get('count_obs', 0))
        },
        'confidence': confidence,
        'used_fallback': (fallback_level != 'exact'),
        'fallback_level': fallback_level
    }


def evaluate_hotel_with_bucket_classification(destination_final, month, week_in_month, 
                                               price_std, baselines_df, price_dist_df=None,
                                               enable_buckets=None):
    """
    Evaluación de precio hotelero consciente de categoría/bucket con cascada de fallbacks jerárquicos.
    """
    if enable_buckets is None:
        enable_buckets = config.ENABLE_PRICE_BUCKETS
    
    if not enable_buckets or price_dist_df is None or 'price_bucket' not in baselines_df.columns:
        result = evaluate_hotel_price(destination_final, month, week_in_month, price_std, baselines_df)
        result['is_deal'] = is_deal(result['z_score'])
        result['price_bucket'] = None
        result['relative_price_index'] = None
        result['market_percentiles'] = None
        return result
    
    # 1. Determinar percentiles y bucket del hotel
    dest_str = str(destination_final)
    dest_dist = price_dist_df[price_dist_df['destination_final'].astype(str) == dest_str]
    
    if dest_dist.empty:
        # Fallback a evaluación no-bucket
        result = evaluate_hotel_price(destination_final, month, week_in_month, price_std, baselines_df)
        result['is_deal'] = is_deal(result['z_score'])
        result['price_bucket'] = None
        result['relative_price_index'] = None
        result['market_percentiles'] = None
        result['message'] = f"No hay distribución previa para {destination_final}"
        return result
    
    dist = dest_dist.iloc[0]
    p25, p50, p75 = float(dist['p25']), float(dist['p50']), float(dist['p75'])
    
    if price_std <= p25:
        price_bucket = 'low'
    elif price_std < p75:
        price_bucket = 'medium'
    else:
        price_bucket = 'high'
        
    rel_index = price_std / p50 if p50 > 0 else np.nan
    
    # 2. Cascada jerárquica de baselines por bucket:
    dest_col = baselines_df['destination_final'].astype(str)
    
    # Nivel 1: Exacto (destino + mes + semana + bucket)
    subset = baselines_df[
        (dest_col == dest_str) &
        (baselines_df['month'] == month) &
        (baselines_df['week_in_month'] == week_in_month) &
        (baselines_df['price_bucket'] == price_bucket)
    ]
    fallback_level = 'exact'
    
    # Nivel 2: Destino + mes + bucket
    if subset.empty:
        subset = baselines_df[
            (dest_col == dest_str) &
            (baselines_df['month'] == month) &
            (baselines_df['price_bucket'] == price_bucket)
        ]
        fallback_level = 'month_bucket'
        
    # Nivel 3: Destino + bucket general
    if subset.empty:
        subset = baselines_df[
            (dest_col == dest_str) &
            (baselines_df['price_bucket'] == price_bucket)
        ]
        fallback_level = 'destination_bucket'
        
    # Nivel 4: Destino + mes + semana (cualquier bucket)
    if subset.empty:
        subset = baselines_df[
            (dest_col == dest_str) &
            (baselines_df['month'] == month) &
            (baselines_df['week_in_month'] == week_in_month)
        ]
        fallback_level = 'context_no_bucket'
        
    # Nivel 5: Destino general
    if subset.empty:
        subset = baselines_df[dest_col == dest_str]
        fallback_level = 'destination_overall'
        
    if subset.empty:
        return {
            'classification': config.CLASSIFICATION_LABELS.get('insufficient_data', 'Insufficient Data'),
            'is_deal': False,
            'z_score': None,
            'price_bucket': price_bucket,
            'relative_price_index': float(rel_index) if pd.notna(rel_index) else None,
            'market_percentiles': {'p25': p25, 'p50': p50, 'p75': p75},
            'baseline_info': None,
            'confidence': 'low',
            'used_fallback': True,
            'fallback_level': 'none'
        }
        
    baseline = subset.iloc[0]
    mean_val = float(baseline['mean_price_std'])
    std_val = float(baseline['std_price_std'])
    if std_val == 0 or pd.isna(std_val):
        std_val = max(mean_val * 0.10, 5.0)
        
    z_score = (price_std - mean_val) / std_val
    classification = classify_deal(z_score)
    
    confidence = 'high' if (not baseline.get('low_confidence', False) and fallback_level == 'exact') else ('medium' if fallback_level in ['month_bucket', 'destination_bucket'] else 'low')
    
    return {
        'classification': classification,
        'is_deal': is_deal(z_score),
        'z_score': float(z_score),
        'price_bucket': price_bucket,
        'relative_price_index': float(rel_index) if pd.notna(rel_index) else None,
        'market_percentiles': {'p25': p25, 'p50': p50, 'p75': p75},
        'baseline_info': {
            'mean': mean_val,
            'std': std_val,
            'count': int(baseline.get('count_obs', 0)),
            'bucket': price_bucket
        },
        'confidence': confidence,
        'used_fallback': (fallback_level != 'exact'),
        'fallback_level': fallback_level
    }


# ========================================
# SAVE & LOAD
# ========================================

def save_baselines(baselines, output_path=None):
    """Guarda baselines en archivo CSV."""
    if output_path is None:
        output_path = config.BASELINES_FILE
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    baselines.to_csv(output_path, index=False)
    logging.info(f"✓ Baselines guardados en: {output_path} ({len(baselines):,} registros)")


def load_baselines(baselines_path=None):
    """Carga baselines desde archivo CSV."""
    if baselines_path is None:
        baselines_path = config.BASELINES_FILE
    baselines_path = Path(baselines_path)
    if not baselines_path.exists():
        # Fallback a outputs/baselines.csv si existe
        alt_path = config.OUTPUT_DIR / "baselines.csv"
        if alt_path.exists():
            baselines_path = alt_path
        else:
            raise FileNotFoundError(f"Baselines no encontrado en {baselines_path} ni en {alt_path}")
    
    baselines = pd.read_csv(baselines_path, dtype={'destination_final': str}, low_memory=False)
    baselines['destination_final'] = baselines['destination_final'].astype(str).str.replace(r'\.0$', '', regex=True)
    logging.info(f"✓ Baselines cargados: {len(baselines):,} contextos desde {baselines_path.name}")
    return baselines
