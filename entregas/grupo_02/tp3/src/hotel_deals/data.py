"""Carga, curación y features de contexto (misma lógica que TP2, con los
parámetros de outliers calibrados solo sobre train)."""

import logging

import numpy as np
import pandas as pd

from . import config

RAW_COLS = [
    "city", "state", "country", "country_code", "date_start", "date_end",
    "number_of_adults", "number_of_rooms", "number_of_kids", "nights",
    "count_repeated", "avg_hotel_count", "avg_price_average",
]
RAW_DTYPES = {"city": str, "state": str, "country": str, "country_code": str}

log = logging.getLogger(__name__)


def load_raw(source="sample"):
    """source='sample' (300k, seed=42) o 'full' (CSV históricos completos)."""
    if source == "sample":
        return pd.read_csv(config.SAMPLE_FILE, usecols=RAW_COLS, dtype=RAW_DTYPES, low_memory=False)
    if source == "full":
        files = sorted(config.HISTORICALS_DIR.glob(config.HISTORICALS_PATTERN))
        if not files:
            raise FileNotFoundError(
                f"No hay {config.HISTORICALS_PATTERN} en {config.HISTORICALS_DIR}. "
                "Descargarlos de Drive o definir HOTEL_DATA_DIR.")
        return pd.concat(
            [pd.read_csv(f, usecols=RAW_COLS, dtype=RAW_DTYPES, low_memory=False) for f in files],
            ignore_index=True)
    raise ValueError(f"source desconocido: {source}")


def compute_price_std(price_total, nights, rooms, adults, kids):
    """USD por habitación-noche-persona (definición TP2)."""
    persons = np.asarray(adults) + np.nan_to_num(np.asarray(kids, dtype=float))
    return np.asarray(price_total, dtype=float) / (np.asarray(nights) * np.asarray(rooms) * persons)


def clean(df):
    """Filtros de validez + precio estándar + piso inferior.

    Devuelve (df_limpio, embudo) con el conteo de filas en cada etapa.
    """
    funnel = [("Datos crudos", len(df))]
    df = df.copy()
    df["number_of_kids"] = df["number_of_kids"].fillna(0)
    valid = (
        (df["nights"] > 0) & (df["nights"] <= config.MAX_NIGHTS)
        & (df["number_of_rooms"] > 0)
        & ((df["number_of_adults"] + df["number_of_kids"]) > 0)
    )
    df = df[valid]
    funnel.append(("Denominadores válidos y noches <= 30", len(df)))

    df = df[(df["avg_price_average"] > 0) & (df["avg_price_average"] <= config.MAX_PRICE_RAW)].copy()
    funnel.append(("Precio total en (0, 50.000] USD", len(df)))

    df["price_std"] = compute_price_std(df["avg_price_average"], df["nights"], df["number_of_rooms"],
                                        df["number_of_adults"], df["number_of_kids"])
    df = df[df["price_std"] >= config.PRICE_STD_FLOOR].copy()
    funnel.append((f"price_std >= {config.PRICE_STD_FLOOR:.0f} USD (piso de error)", len(df)))
    return df, pd.DataFrame(funnel, columns=["etapa", "filas"])


def stay_duration(nights):
    nights = np.asarray(nights)
    return np.where(nights <= 2, "corta", np.where(nights <= 5, "media", "larga"))


def week_in_month(day):
    day = np.asarray(day)
    w = np.ones(len(day), dtype=int)
    w[(day >= 8) & (day <= 15)] = 2
    w[(day >= 16) & (day <= 22)] = 3
    w[day >= 23] = 4
    return w


def add_features(df):
    """Contexto temporal sobre el día de check-in (0=Lunes ... 6=Domingo)."""
    df = df.copy()
    d = pd.to_datetime(df["date_start"])
    df["date_start"] = d
    df["year"] = d.dt.year
    df["month"] = d.dt.month
    df["day_of_week"] = d.dt.dayofweek
    df["week_in_month"] = week_in_month(d.dt.day.values)
    df["stay_duration"] = stay_duration(df["nights"].values)
    return df


class WinsorCap:
    """Corte superior de price_std estimado sobre train y aplicado a cualquier período."""

    def __init__(self, quantile=config.WINSOR_QUANTILE):
        self.quantile = quantile
        self.cap_ = None

    def fit(self, df):
        self.cap_ = float(df["price_std"].quantile(self.quantile)) if self.quantile else np.inf
        return self

    def transform(self, df):
        df = df.copy()
        df["price_std"] = df["price_std"].clip(upper=self.cap_)
        df["log_price"] = np.log(df["price_std"])
        return df


def prepare(source, mapper):
    """Datos curados con mapping y features, todavía sin winsorizar."""
    raw = load_raw(source)
    df, funnel = clean(raw)
    df = mapper.transform(df)
    df = add_features(df)
    df = df.reset_index(drop=True)
    df["row_id"] = np.arange(len(df))
    return df, funnel
