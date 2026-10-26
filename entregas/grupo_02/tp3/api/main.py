"""API de detección de ofertas hoteleras (FastAPI).

    uvicorn api.main:app --host 0.0.0.0 --port 8000

Endpoints:
    GET  /health          estado y parámetros del modelo servido
    POST /evaluate        evalúa una búsqueda
    POST /evaluate/batch  evalúa una lista de búsquedas
"""

import sys
from datetime import date
from pathlib import Path
from typing import List, Optional

import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hotel_deals.service import DealDetector  # noqa: E402

app = FastAPI(
    title="Hotel Deals Detector — Grupo 2",
    description="Clasifica si el precio de una búsqueda hotelera es una oferta para su contexto "
                "(destino x mes x semana x estadía, con cascada de fallback).",
    version="1.0.0",
)
detector = DealDetector()


class Query(BaseModel):
    city: Optional[str] = Field(None, examples=["Miami Beach"])
    state: Optional[str] = Field(None, examples=["Florida"])
    country: Optional[str] = Field(None, examples=["United States"])
    country_code: str = Field(..., description="ISO-3166 alfa-2", examples=["US"])
    date_start: date = Field(..., description="Fecha de check-in", examples=["2025-07-10"])
    nights: int = Field(..., examples=[3])
    adults: int = Field(..., examples=[2])
    kids: int = Field(0, examples=[0])
    rooms: int = Field(1, examples=[1])
    price_total: float = Field(..., description="Precio total de la estadía en USD", examples=[540.0])


class Response(BaseModel):
    decision: str = Field(..., description="deal | no_deal | insufficient_data | invalid_price | invalid_input")
    is_deal: Optional[bool]
    price_std: Optional[float] = Field(None, description="USD por habitación-noche-persona")
    baseline_median: Optional[float]
    discount: Optional[float] = Field(None, description="1 - price_std / mediana del contexto")
    z_log: Optional[float]
    baseline_level: str
    baseline_n_records: Optional[float]
    destination_final: Optional[str]
    destination_name: Optional[str]
    is_mapped: bool
    explanation: str = Field(..., description="Justificación legible de la decisión")


@app.get("/health")
def health():
    return {"status": "ok", "model": "hibrido_cascada", "params": detector.params}


@app.post("/evaluate", response_model=Response)
def evaluate(q: Query):
    return detector.evaluate(q.model_dump())


@app.post("/evaluate/batch", response_model=List[Response])
def evaluate_batch(qs: List[Query]):
    if not qs:
        return []
    res = detector.evaluate_frame(pd.DataFrame([q.model_dump() for q in qs]))
    res = res.astype(object).where(res.notna(), None)
    return res.to_dict(orient="records")
