# query_historicos.py
# Script para extraer datos históricos de la base de datos

import pandas as pd
import psycopg2
import sys
import logging
import config

# Configurar logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format=config.LOG_FORMAT
)

def dbConnect():
    """Conecta a la base de datos PostgreSQL."""
    try:
        cnx = psycopg2.connect(
            host=config.DB_CONFIG['host'],
            port=config.DB_CONFIG['port'],
            user=config.DB_CONFIG['user'],
            password=config.DB_CONFIG['password'],
            database=config.DB_CONFIG['database']
        )
        logging.info('✓ Conexión exitosa a la base de datos')
        return cnx
    except Exception as e:
        logging.error(f"Error al conectar: {e}")
        return None


def getData(cnx, year):
    """
    Ejecuta query para extraer datos históricos de un año.
    
    Args:
        cnx: Conexión a base de datos
        year: Año a extraer (e.g., 2025)
    
    Returns:
        DataFrame con datos
    """
    query = f"""
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
        COUNT(*) AS count_repeated,  
        AVG(a.hotel_count) AS avg_hotel_count,
        MIN(a.hotel_count) AS min_hotel_count,
        MAX(a.hotel_count) AS max_hotel_count,
        AVG(a.price_average) AS avg_price_average,
        MAX(a.price_high) AS max_price_high,
        MIN(a.price_low) AS min_price_low
    FROM 
        analytic.customer_shopping_model AS a
    JOIN 
        analytic.hotel_city_location AS h
    ON 
        a.hotel_id = h.hotel_id
    WHERE 
        a.date_start >= '{year}-01-01' 
        AND a.date_start < '{year + 1}-01-01'
        AND a.date_end >= '{year}-01-01' 
        AND a.date_end < '{year + 1}-01-01'
        AND a.type = 'HOTELS'
    GROUP BY 
        h.city, 
        a.date_start, 
        a.date_end, 
        a.number_of_adults, 
        a.number_of_kids, 
        a.number_of_rooms,
        a.nights, 
        h.state, 
        h.country, 
        h.country_code;
    """
    
    try:
        logging.info(f"Ejecutando query para año {year}...")
        df = pd.read_sql(query, cnx)
        logging.info(f"Query exitosa: {len(df):,} registros obtenidos")
        return df
    except Exception as e:
        logging.error(f"Error al ejecutar query: {e}")
        return None
    finally:
        if cnx:
            cnx.close()
            logging.debug('Conexión cerrada')


def main(year):
    """
    Ejecuta extracción de datos para un año.
    
    Args:
        year: Año a extraer
    """
    logging.info("="*60)
    logging.info(f"EXTRACCIÓN DE DATOS HISTÓRICOS - AÑO {year}")
    logging.info("="*60)
    
    # Conectar
    connection = dbConnect()
    if connection is None:
        sys.exit(1)
    
    # Extraer datos
    datos = getData(connection, year)
    
    if datos is not None:
        # Guardar
        output_file = config.PRICE_HISTORICALS_DIR / f'historicals_{year}.csv'
        datos.to_csv(output_file, index=False)
        
        logging.info("="*60)
        logging.info("✓ EXTRACCIÓN COMPLETADA")
        logging.info("="*60)
        logging.info(f"  Archivo: {output_file}")
        logging.info(f"  Registros: {len(datos):,}")
        logging.info(f"  Ciudades únicas: {datos['city'].nunique():,}")
        logging.info(f"  Rango fechas: {datos['date_start'].min()} a {datos['date_start'].max()}")
        logging.info("="*60)
    else:
        logging.error("No se obtuvieron datos")
        sys.exit(1)


if __name__ == "__main__":
    # Por defecto extraer 2025
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
    main(year)
