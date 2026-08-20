# database.py
# Optimización SQLite - TODO en SQL, sin pandas para cálculos pesados

import sqlite3
import csv
import logging
import time
from pathlib import Path
import config

DB_PATH = Path(config.BASE_DIR) / 'data' / 'hotel_data.db'


def get_connection():
    """Obtiene conexión a SQLite."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-64000")
    return conn


def init_and_load(force_reload=False):
    """
    Inicializa DB y carga CSVs directamente.
    Retorna True si ya existían datos.
    """
    conn = get_connection()
    
    # Verificar si ya hay datos
    try:
        count = conn.execute("SELECT COUNT(*) FROM raw_data").fetchone()[0]
        if count > 0 and not force_reload:
            logging.info(f"Base de datos ya tiene {count:,} registros.")
            conn.close()
            return True
    except sqlite3.OperationalError:
        pass
    
    # Crear tabla
    conn.execute("DROP TABLE IF EXISTS raw_data")
    conn.execute("""
        CREATE TABLE raw_data (
            city TEXT,
            state TEXT,
            country TEXT,
            country_code TEXT,
            date_start TEXT,
            date_end TEXT,
            number_of_adults INTEGER,
            number_of_rooms INTEGER,
            number_of_kids INTEGER,
            nights INTEGER,
            count_repeated INTEGER,
            avg_hotel_count REAL,
            min_hotel_count INTEGER,
            max_hotel_count INTEGER,
            avg_price_average REAL,
            max_price_high REAL,
            min_price_low REAL,
            source_file TEXT
        )
    """)
    conn.commit()
    
    # Cargar CSVs
    import glob
    pattern = str(Path(config.PRICE_HISTORICALS_DIR) / config.HISTORICALS_FILE_PATTERN)
    files = glob.glob(pattern)
    
    if not files:
        conn.close()
        raise FileNotFoundError(f"No files found")
    
    logging.info(f"Cargando {len(files)} archivos CSV...")
    
    for file in sorted(files):
        logging.info(f"  {Path(file).name}...")
        
        with open(file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            
            batch = []
            for row in reader:
                if len(row) < 17:
                    continue
                try:
                    batch.append((
                        row[0], row[1], row[2], row[3],
                        row[4], row[5],
                        int(float(row[6])),  # adults
                        int(float(row[7])),  # rooms
                        int(float(row[8])),  # kids
                        int(float(row[9])),  # nights
                        int(float(row[10])), # count_repeated
                        float(row[11]),      # avg_hotel_count
                        int(float(row[12])), # min_hotel_count
                        int(float(row[13])), # max_hotel_count
                        float(row[14]),      # avg_price
                        float(row[15]),      # max_price
                        float(row[16]),      # min_price
                        Path(file).name
                    ))
                except (ValueError, IndexError):
                    continue
                
                if len(batch) >= 50000:
                    conn.executemany("INSERT INTO raw_data VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", batch)
                    batch = []
            
            if batch:
                conn.executemany("INSERT INTO raw_data VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", batch)
        
        conn.commit()
        count = conn.execute("SELECT COUNT(*) FROM raw_data").fetchone()[0]
        logging.info(f"    Total: {count:,}")
    
    conn.close()
    return False


def calculate_baselines_sql():
    """
    Calcula baselines COMPLETAMENTE en SQL.
    Incluye: validación, estandarización, mapeo, y cálculo estadístico.
    Sin expandir fechas - mucho más rápido.
    """
    import pandas as pd
    
    conn = get_connection()
    
    # Cargar mapping
    mapping_df = pd.read_csv(config.DESTINATION_MAPPING_FILE)
    mapping_df.to_sql('mapping', conn, if_exists='replace', index=False)
    
    # Query completo: estandariza, mapea, agrupa
    query = """
    WITH valid_data AS (
        SELECT *
        FROM raw_data
        WHERE nights > 0 
            AND number_of_rooms > 0 
            AND (number_of_adults + number_of_kids) > 0
    ),
    standardized AS (
        SELECT 
            *,
            avg_price_average / (nights * number_of_rooms * MAX(number_of_adults + number_of_kids, 1)) as price_std,
            CAST(strftime('%m', date_start) AS INTEGER) as month,
            CASE 
                WHEN CAST(strftime('%d', date_start) AS INTEGER) <= 7 THEN 1
                WHEN CAST(strftime('%d', date_start) AS INTEGER) <= 15 THEN 2
                WHEN CAST(strftime('%d', date_start) AS INTEGER) <= 22 THEN 3
                ELSE 4
            END as week_in_month
        FROM valid_data
    ),
    with_destination AS (
        SELECT 
            s.*,
            COALESCE(
                m3.nearest_destination_id,
                m2.nearest_destination_id,
                m1.nearest_destination_id,
                s.city
            ) as destination_final,
            COALESCE(
                m3.nearest_destination_name,
                m2.nearest_destination_name,
                m1.nearest_destination_name,
                s.city
            ) as destination_name
        FROM standardized s
        LEFT JOIN mapping m3 ON UPPER(s.country_code) || ' - ' || UPPER(s.state) || ' - ' || s.city = m3.reference
        LEFT JOIN mapping m2 ON UPPER(s.country_code) || ' - ' || s.city = m2.reference
        LEFT JOIN mapping m1 ON UPPER(s.country_code) || ' - ' || UPPER(s.state) = m1.reference
    )
    SELECT 
        destination_final,
        destination_name,
        month,
        week_in_month,
        AVG(price_std) as mean_price_std,
        SQRT(MAX(0, AVG(price_std * price_std) - AVG(price_std) * AVG(price_std))) as std_price_std,
        MIN(price_std) as min_price_std,
        MAX(price_std) as max_price_std,
        COUNT(*) as count_obs,
        SUM(count_repeated) as total_repeated
    FROM with_destination
    WHERE destination_final IS NOT NULL
    GROUP BY destination_final, month, week_in_month
    """
    
    logging.info("Calculando baselines via SQL...")
    start = time.time()
    
    baselines = pd.read_sql_query(query, conn)
    
    elapsed = time.time() - start
    logging.info(f"✓ Baselines calculados: {len(baselines):,} contextos en {elapsed:.1f}s")
    
    conn.close()
    return baselines


def get_data_summary():
    """Retorna resumen de la base de datos."""
    conn = get_connection()
    
    try:
        count = conn.execute("SELECT COUNT(*) FROM raw_data").fetchone()[0]
        cities = conn.execute("SELECT COUNT(DISTINCT city) FROM raw_data").fetchone()[0]
        date_range = conn.execute("SELECT MIN(date_start), MAX(date_end) FROM raw_data").fetchone()
        
        conn.close()
        return {
            'total_records': count,
            'unique_cities': cities,
            'date_range': date_range
        }
    except sqlite3.OperationalError as e:
        conn.close()
        return {'error': str(e)}


if __name__ == "__main__":
    print("="*60)
    print("SQLite Optimization Test")
    print("="*60)
    
    # 1. Init and load
    start = time.time()
    init_and_load(force_reload=True)
    load_time = time.time() - start
    
    summary = get_data_summary()
    print(f"\nLoad time: {load_time:.1f}s")
    print(f"Records: {summary.get('total_records', 0):,}")
    
    # 2. Calculate baselines
    start = time.time()
    baselines = calculate_baselines_sql()
    calc_time = time.time() - start
    
    print(f"\nBaseline calculation: {calc_time:.1f}s")
    print(f"Baselines: {len(baselines):,}")
    print(f"Destinations: {baselines['destination_final'].nunique():,}")
    
    # 3. Top destinations
    print(f"\nTop 10 destinations:")
    top = baselines.groupby('destination_name')['count_obs'].sum().nlargest(10)
    for name, count in top.items():
        print(f"  {name:30s}: {count:,}")
    
    print(f"\nTotal time: {load_time + calc_time:.1f}s")
