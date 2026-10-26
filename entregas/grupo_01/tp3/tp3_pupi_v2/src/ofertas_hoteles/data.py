"""Carga, limpieza y features.

Unidad de análisis: **una búsqueda original** (una fila del CSV crudo).
No se expande a noches: la decisión "¿es oferta?" se toma por consulta, y la
expansión repetía el mismo precio en varias filas (inflaba soporte y generaba
contextos sin dispersión). El contexto temporal es el mes de check-in
(solo 5,8% de las estadías cruza de mes).
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from . import config
from .mapping import DestinationMapper

log = logging.getLogger(__name__)

USECOLS = [
    "city", "state", "country", "country_code", "date_start", "date_end",
    "number_of_adults", "number_of_rooms", "number_of_kids", "nights",
    "count_repeated", "avg_price_average",
]
DTYPES = {"city": str, "state": str, "country": str, "country_code": str, "date_start": str, "date_end": str}


def load_sample(path: Path, frac: float, seed: int = config.SEED, chunksize: int = config.CHUNKSIZE) -> pd.DataFrame:
    """Lee el CSV en pedazos y se queda con una fracción aleatoria (reproducible) de cada pedazo.
    Nunca carga el archivo entero en memoria."""
    parts = []
    reader = pd.read_csv(path, usecols=USECOLS, dtype=DTYPES, chunksize=chunksize, low_memory=False)
    for i, chunk in enumerate(reader):
        parts.append(chunk.sample(frac=frac, random_state=seed + i) if frac < 1 else chunk)
    df = pd.concat(parts, ignore_index=True)
    log.info("%s: %s filas muestreadas (frac=%.2f)", path.name, f"{len(df):,}", frac)
    return df


def clean(df: pd.DataFrame, year_tag: str) -> tuple[pd.DataFrame, dict]:
    """Filtros de validez (solo descartan filas imposibles de usar: sin noches, sin precio, fechas incoherentes).
    NO se eliminan duplicados ni valores extremos: todos los datos válidos quedan en las bases.
    Devuelve el df y un resumen de cuántas filas quedaron (y cuántas repeticiones exactas hay, solo informativo)."""
    n0 = len(df)
    x = df.copy()
    for c in ["number_of_adults", "number_of_rooms", "number_of_kids", "nights", "count_repeated", "avg_price_average"]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x["number_of_kids"] = x["number_of_kids"].fillna(0)
    x["date_start"] = pd.to_datetime(x["date_start"], errors="coerce")
    x["date_end"] = pd.to_datetime(x["date_end"], errors="coerce")

    ok = (
        (x["nights"] > 0) & (x["number_of_rooms"] > 0) & (x["number_of_adults"] + x["number_of_kids"] > 0)
        & np.isfinite(x["avg_price_average"]) & (x["avg_price_average"] > 0)
        & ((x["date_end"] - x["date_start"]).dt.days == x["nights"])
    )
    x = x[ok]
    n_valid = len(x)

    # Repeticiones exactas (misma geografía, fechas, ocupación y precio): se CUENTAN pero no se eliminan
    key = ["country_code", "state", "city", "date_start", "nights", "number_of_adults",
           "number_of_kids", "number_of_rooms", "avg_price_average"]
    n_rep = int(x.duplicated(subset=key).sum())
    x = x.reset_index(drop=True)
    x["search_id"] = [f"{year_tag}_{i}" for i in range(len(x))]
    resumen = {"filas_muestra": n0, "filas_validas": n_valid, "filas_descartadas": n0 - n_valid,
               "repeticiones_exactas_conservadas": n_rep}
    return x, resumen


def comparable_price(df: pd.DataFrame, unit: str = config.PRICE_UNIT) -> pd.Series:
    if unit == "habitacion_noche":
        return df["avg_price_average"].astype(float)
    if unit == "formula_completa":
        persons = (df["number_of_adults"] + df["number_of_kids"]).clip(lower=1)
        return df["avg_price_average"] / (df["nights"] * df["number_of_rooms"] * persons)
    if unit == "repo":
        # réplica EXACTA de auxiliary_functions.standardize_prices con config.STANDARDIZATION_RULES del repo
        # (threshold 1 / fallback 0 en noches y habitaciones): con 1 noche o 1 habitación el producto da 0 → no divide.
        nights = df["nights"].where(df["nights"] > 1, 0)
        rooms = df["number_of_rooms"].where(df["number_of_rooms"] > 1, 0)
        adults = df["number_of_adults"].where(df["number_of_adults"] > 1, 1)
        persons = (adults + df["number_of_kids"].fillna(0)).replace(0, 1)
        return df["avg_price_average"] / (nights * rooms * persons).replace(0, 1)
    raise ValueError(f"PRICE_UNIT desconocida: {unit}")


def add_features(df: pd.DataFrame, mapper: DestinationMapper) -> pd.DataFrame:
    """Destino canónico, país, mes, semana del mes y ocupación. Ninguna usa el precio."""
    x = mapper.map_dataframe(df)
    x["price"] = comparable_price(x)
    x["log_price"] = np.log(x["price"])
    x["month"] = x["date_start"].dt.month.astype(int)
    day = x["date_start"].dt.day
    x["week_in_month"] = np.select([day <= 7, day <= 15, day <= 22], [1, 2, 3], default=4)
    x["persons"] = (x["number_of_adults"] + x["number_of_kids"]).astype(int)
    x["pax_per_room"] = x["persons"] / x["number_of_rooms"]
    return x


def build_samples(raw_dir: Path = config.RAW_DIR, out_dir: Path = config.INTERIM_DIR) -> dict:
    """Paso 1: muestra 2024 (train) y 2025 (val/test) limpias y con features. Guarda parquet."""
    out_dir.mkdir(parents=True, exist_ok=True)
    mapper = DestinationMapper(config.MAPPING_PATH)
    resumen = {}
    for year, frac in [(2024, config.FRAC_TRAIN_2024), (2025, config.FRAC_2025)]:
        raw = load_sample(raw_dir / config.RAW_FILES[year], frac)
        x, r = clean(raw, str(year))
        x = add_features(x, mapper)
        # Solo nos quedamos con check-in del año correspondiente (separación temporal estricta)
        n_antes = len(x)
        x = x[x["date_start"].dt.year == year].reset_index(drop=True)
        r["filas_checkin_otro_anio"] = n_antes - len(x)
        r["filas_finales"] = len(x)
        r["pct_mapeado"] = round(100 * x["is_mapped"].mean(), 2)
        r["pct_demanda_mapeada"] = round(100 * x.loc[x["is_mapped"], "count_repeated"].sum() / x["count_repeated"].sum(), 2)
        resumen[year] = r
        x.to_parquet(out_dir / f"muestra_{year}.parquet", index=False)
        log.info("%s → %s", year, r)
    return resumen
