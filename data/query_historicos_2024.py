# Imports
import pandas as pd
import os
import psycopg2

# Definir el directorio de salida para el archivo CSV
DATAPATH = os.path.expanduser("~/Desktop/hotels/data")

# Credenciales de conexión a la base de datos
# Configurar via variables de entorno o completar manualmente
HOST = os.getenv('DB_HOST', 'your-dwh-host.example.com')
PORT = int(os.getenv('DB_PORT', 5432))
DB_NAME = os.getenv('DB_NAME', 'your_database')
USER = os.getenv('DB_USER', 'your_user')
PASSWORD = os.getenv('DB_PASSWORD', '')

# Año para la consulta
YEAR = 2024

# Función para conectarse a la base de datos
def dbConnect(HOST, PORT, DB_NAME, USER, PASSWORD):
    try:
        cnx = psycopg2.connect(
            host=HOST,
            port=PORT,
            user=USER,
            password=PASSWORD,
            database=DB_NAME
        )
        print('Conexión exitosa')
        return cnx
    except Exception as e:
        print(f"Error al conectar: {e}")
        return None

# Función para ejecutar la consulta y obtener los datos
def getData(cnx, year):
    try:
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
        df = pd.read_sql(query, cnx)
        return df
    except Exception as e:
        print(f"Error al ejecutar la consulta: {e}")
        return None
    finally:
        if cnx is not None:
            cnx.close()
            print('Conexión cerrada')

# Ejecutar el script principal
if __name__ == "__main__":
    connection = dbConnect(HOST, PORT, DB_NAME, USER, PASSWORD)
    
    if connection is not None:
        datos = getData(connection, YEAR)
        
        if datos is not None:
            # Guardar los datos en un archivo CSV con el año en el nombre
            output_file = os.path.join(DATAPATH, f'datos_historicos_{YEAR}.csv')
            datos.to_csv(output_file, index=False)
            print(f"Datos guardados en: {output_file}")
        else:
            print("No se obtuvieron datos.")
    else:
        print("No se pudo establecer la conexión con la base de datos.")