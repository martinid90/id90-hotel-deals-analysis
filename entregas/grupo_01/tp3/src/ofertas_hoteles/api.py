"""API del detector de ofertas.

    uvicorn ofertas_hoteles.api:app --host 0.0.0.0 --port 8000
    → documentación interactiva en http://localhost:8000/docs
"""
from __future__ import annotations

from datetime import date
from functools import lru_cache
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator

from .scorer import DealScorer

app = FastAPI(
    title="Detector de ofertas hoteleras - TP3 Grupo 1 (Pupi v2)",
    description="Dado un precio de hotel y su contexto (lugar, fecha, ocupación), responde si es una oferta "
                "para su mercado. Modelo: mediana/MAD robusto por destino × mes con fallback jerárquico.",
    version="2.0.0",
)


@lru_cache(maxsize=1)
def get_scorer() -> DealScorer:
    return DealScorer()


class Query(BaseModel):
    city: str = Field(..., min_length=1, examples=["Orlando"], description="Ciudad tal como viene en la búsqueda")
    state: Optional[str] = Field(None, examples=["Florida"], description="Estado/provincia (mejora el mapeo)")
    country: Optional[str] = Field(None, examples=["United States of America"])
    country_code: str = Field(..., min_length=2, max_length=3, examples=["us"], description="Código ISO del país")
    date_start: date = Field(..., examples=["2025-07-10"], description="Fecha de check-in (YYYY-MM-DD)")
    date_end: Optional[date] = Field(None, examples=["2025-07-13"], description="Fecha de check-out")
    nights: Optional[int] = Field(None, ge=1, le=60, description="Noches (si no se manda date_end)")
    adults: int = Field(2, ge=1, le=20)
    kids: int = Field(0, ge=0, le=20)
    rooms: int = Field(1, ge=1, le=20)
    price: float = Field(..., gt=0, lt=1_000_000, examples=[95.0],
                         description="Precio promedio por habitación y por noche en USD (avg_price_average). "
                                     "Se compara tal cual: noches, habitaciones y personas no lo dividen.")

    @model_validator(mode="after")
    def _check_dates(self):
        if self.date_end is not None:
            n = (self.date_end - self.date_start).days
            if n < 1:
                raise ValueError("date_end debe ser posterior a date_start")
            if self.nights is not None and self.nights != n:
                raise ValueError("nights no coincide con date_end - date_start")
            self.nights = n
        if self.nights is None:
            self.nights = 1
        return self


class Destino(BaseModel):
    id: str
    nombre: str
    mapeado: bool
    match_level: str
    pais: str


class Prediction(BaseModel):
    oferta: Literal["SI", "NO"] = Field(..., description="Respuesta final: SI si el precio es una oferta para su mercado")
    decision: Literal["oferta", "normal", "sospechoso", "sin_soporte"]
    is_deal: bool
    mensaje: str
    precio_comparable: float = Field(..., description="Precio por habitación-noche usado para comparar (no se divide)")
    noches: int = Field(..., description="Noches de la estadía (se informa para trazar el contexto; no cambia el cálculo)")
    precio_referencia: Optional[float]
    descuento: Optional[float] = Field(None, description="1 - precio / precio típico")
    z_robusto: Optional[float]
    nivel_contexto: str
    confianza: Literal["alta", "media", "baja", "ninguna"]
    n_referencia: Optional[int] = Field(None, description="Búsquedas de 2024 con las que se calculó la referencia")
    demanda_referencia: Optional[int] = Field(None, description="Demanda de esas búsquedas (suma de count_repeated)")
    destino: Destino


def _predict(q: Query) -> dict:
    try:
        res = get_scorer().score_query(
            city=q.city, state=q.state, country=q.country, country_code=q.country_code, date_start=q.date_start,
            nights=q.nights, adults=q.adults, kids=q.kids, rooms=q.rooms, price=q.price)
    except Exception as exc:  # fallback final: nunca romper en producción, pero avisar
        res = {"decision": "sin_soporte", "is_deal": False, "mensaje": f"No se pudo evaluar: {type(exc).__name__}",
                "precio_comparable": q.price, "noches": q.nights, "precio_referencia": None, "descuento": None, "z_robusto": None,
                "nivel_contexto": "sin_soporte", "confianza": "ninguna", "n_referencia": None, "demanda_referencia": None,
                "destino": {"id": "desconocido", "nombre": q.city, "mapeado": False, "match_level": "error", "pais": q.country_code.upper()}}
    # la respuesta arranca con el veredicto binario
    return {"oferta": "SI" if res["is_deal"] else "NO", **res}


@app.get("/health")
def health():
    s = get_scorer()
    return {"status": "ok", "modelo": s.meta["modelo"], "version": s.meta["version"]}


@app.get("/model")
def model_info():
    return get_scorer().meta


@app.post("/predict", response_model=Prediction)
def predict(q: Query):
    return _predict(q)


@app.post("/predict/batch", response_model=list[Prediction])
def predict_batch(qs: list[Query]):
    if len(qs) > 1000:
        raise HTTPException(status_code=413, detail="Máximo 1000 consultas por request")
    return [_predict(q) for q in qs]
