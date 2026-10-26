# API del detector de ofertas (TP3 Grupo 1 - Pupi v2)
# Build:  docker build -t ofertas-hoteles:tp3 .
# Run:    docker run --rm -p 8000:8000 ofertas-hoteles:tp3
# Docs:   http://localhost:8000/docs
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    TP3_PROJECT_DIR=/app \
    TP3_MODELS_DIR=/app/models \
    TP3_MAPPING_PATH=/app/data/destination_with_nearest.csv

WORKDIR /app

COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --no-deps .

# Artefactos del modelo final (entrenado con 2024) y tabla de mapeo de destinos
COPY models ./models
COPY data/destination_with_nearest.csv ./data/destination_with_nearest.csv

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "ofertas_hoteles.api:app", "--host", "0.0.0.0", "--port", "8000"]
