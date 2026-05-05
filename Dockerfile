FROM python:3.10-slim

WORKDIR /app

# Copiar requirements e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todos los scripts Python del proyecto
COPY config.py .
COPY auxiliary_functions.py .
COPY app.py .
COPY query_historicos.py .
COPY pipeline_build_baselines.py .

# Crear estructura completa de directorios
RUN mkdir -p data/price_historicals \
             data/destination_mapping \
             outputs/logs \
             notebooks

# Variable de entorno para logging
ENV LOG_LEVEL=DEBUG

# Exponer puerto de Streamlit
EXPOSE 8501

# Healthcheck
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Comando por defecto (app Streamlit)
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
