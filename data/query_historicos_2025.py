# query_historicos_2025.py
# Extrae datos históricos del año 2025 desde PostgreSQL.
# Credenciales leídas desde .env en la raíz del proyecto.

import pandas as pd
import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

# Cargar .env desde la raíz del proyecto (un nivel arriba de data/)
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

HOST     = os.getenv('DB_HOST')
PORT     = int(os.getenv('DB_PORT', 5432))
DB_NAME  = os.getenv('DB_NAME')
USER     = os.getenv('DB_USER')
PASSWORD = os.getenv('DB_PASSWORD')

YEAR     = 2025
DATAPATH = Path(__file__).resolve().parent


def dbConnect(host, port, db_name, user, password):
    """Conecta a la base de datos PostgreSQL."""
    try:
        cnx = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=db_name
        )
        print('✓ Conexión exitosa')
        return cnx
    except Exception as e:
        print(f"✗ Error al conectar: {e}")
        return None


def getData(cnx, year):
    """
    Extrae el resumen estadístico de búsquedas de tipo HOTELS para el año indicado.
    Devuelve una fila por combinación única de (destino, fechas, ocupación).
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
        COUNT(*)             AS count_repeated,  
        AVG(a.hotel_count)   AS avg_hotel_count,
        MIN(a.hotel_count)   AS min_hotel_count,
        MAX(a.hotel_count)   AS max_hotel_count,
        AVG(a.price_average) AS avg_price_average,
        MAX(a.price_high)    AS max_price_high,
        MIN(a.price_low)     AS min_price_low
    FROM 
        analytic.customer_shopping_model AS a
    JOIN 
        analytic.hotel_city_location AS h ON a.hotel_id = h.hotel_id
    WHERE 
        a.date_start >= '{year}-01-01' 
        AND a.date_start <  '{year + 1}-01-01'
        AND a.date_end   >= '{year}-01-01' 
        AND a.date_end   <  '{year + 1}-01-01'
        AND a.type = 'HOTELS'
    GROUP BY 
        h.city, h.state, h.country, h.country_code,
        a.date_start, a.date_end, 
        a.number_of_adults, a.number_of_kids, a.number_of_rooms, a.nights;
    """
    try:
        print(f"  Ejecutando query para {year}... (puede tardar varios minutos)")
        df = pd.read_sql(query, cnx)
        print(f"  ✓ {len(df):,} registros obtenidos")
        return df
    except Exception as e:
        print(f"  ✗ Error al ejecutar la query: {e}")
        return None
    finally:
        if cnx:
            cnx.close()
            print("  Conexión cerrada")


if __name__ == "__main__":
    print("=" * 55)
    print(f"  EXTRACCIÓN HISTÓRICOS — AÑO {YEAR}")
    print("=" * 55)

    if not HOST or not USER or not PASSWORD:
        print(f"✗ Credenciales no encontradas.")
        print(f"  Buscando .env en: {env_path}")
        exit(1)

    print(f"  Host : {HOST}")
    print(f"  DB   : {DB_NAME}")
    print(f"  User : {USER}")
    print()

    connection = dbConnect(HOST, PORT, DB_NAME, USER, PASSWORD)

    if connection:
        datos = getData(connection, YEAR)
        if datos is not None:
            output_file = DATAPATH / f'datos_historicos_{YEAR}.csv'
            datos.to_csv(output_file, index=False)
            print()
            print("=" * 55)
            print("  ✓ EXTRACCIÓN COMPLETADA")
            print(f"  Archivo  : {output_file}")
            print(f"  Filas    : {len(datos):,}")
            print(f"  Ciudades : {datos['city'].nunique():,} únicas")
            print(f"  Fechas   : {datos['date_start'].min()} → {datos['date_start'].max()}")
            print("=" * 55)
        else:
            print("✗ No se obtuvieron datos.")
    else:
        print("✗ No se pudo conectar a la base de datos.")
