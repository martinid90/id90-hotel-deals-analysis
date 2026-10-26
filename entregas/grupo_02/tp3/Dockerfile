FROM python:3.10-slim

WORKDIR /app

COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# Solo lo necesario para servir: código, mapping geográfico y baselines entrenados.
# Los datos de entrenamiento no entran en la imagen.
COPY src/ src/
COPY api/ api/
COPY data/destination_with_nearest.csv data/
COPY artifacts/ artifacts/

EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
