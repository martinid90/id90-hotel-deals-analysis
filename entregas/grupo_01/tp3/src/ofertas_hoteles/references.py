"""Referencias de mercado por contexto (se calculan SOLO con train) y fallback jerárquico."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def fit_level_tables(train: pd.DataFrame, levels: list[tuple[str, list[str]]]) -> dict[str, pd.DataFrame]:
    """Para cada nivel: n búsquedas, demanda (suma de count_repeated), mediana y MAD del log-precio, media y desvío.
    La demanda se informa (cuánta gente buscó ese contexto) pero las referencias se calculan sin ponderar."""
    tables = {}
    for name, keys in levels:
        x = train[keys + ["log_price"]].copy()
        x["demanda"] = train["count_repeated"].fillna(1).values if "count_repeated" in train else 1
        med = x.groupby(keys)["log_price"].transform("median")
        x["abs_dev"] = (x["log_price"] - med).abs()
        t = (
            x.groupby(keys)
            .agg(n=("log_price", "size"), demanda=("demanda", "sum"), med_log=("log_price", "median"), mad_log=("abs_dev", "median"),
                 mean_log=("log_price", "mean"), std_log=("log_price", "std"))
            .reset_index()
        )
        tables[name] = t
    return tables


def resolve(df: pd.DataFrame, tables: dict[str, pd.DataFrame], levels, min_support: int = config.MIN_SUPPORT,
            require_std: bool = False) -> pd.DataFrame:
    """Para cada fila elige el nivel más fino con al menos `min_support` búsquedas.
    Devuelve: level, n_ref, med_log, mad_log, mean_log, std_log (NaN si no hay soporte)."""
    out = pd.DataFrame(index=df.index)
    out["level"] = "sin_soporte"
    for col in ["n_ref", "med_log", "mad_log", "mean_log", "std_log"]:
        out[col] = np.nan
    pending = np.ones(len(df), dtype=bool)
    for name, keys in levels:
        m = df[keys].merge(tables[name], on=keys, how="left")
        ok = (m["n"].values >= min_support) & pending
        if require_std:
            ok &= (m["std_log"].values > 0)
        idx = out.index[ok]
        out.loc[idx, "level"] = name
        out.loc[idx, "n_ref"] = m["n"].values[ok]
        for col in ["med_log", "mad_log", "mean_log", "std_log"]:
            out.loc[idx, col] = m[col].values[ok]
        pending &= ~ok
    return out


# ---------------------------------------------------------------------------
# price_bucket (Escenario B): cortes p25/p75 por destino calculados SOLO con train
# ---------------------------------------------------------------------------
def fit_bucket_cuts(train: pd.DataFrame, min_support: int = config.MIN_SUPPORT) -> pd.DataFrame:
    g = train.groupby("destination_final")["price"]
    cuts = pd.concat([g.size().rename("n"), g.quantile(0.25).rename("p25"), g.quantile(0.75).rename("p75")], axis=1)
    return cuts[cuts["n"] >= min_support].reset_index()[["destination_final", "p25", "p75"]]


def assign_bucket(df: pd.DataFrame, cuts: pd.DataFrame, price_col: str = "price") -> pd.Series:
    """Asigna el bucket con los cortes de train al precio que se está evaluando
    (es lo que pasaría en producción: el precio nuevo define su bucket)."""
    m = df[["destination_final"]].merge(cuts, on="destination_final", how="left")
    p = df[price_col].values
    b = np.select([p <= m["p25"].values, p >= m["p75"].values], ["low", "high"], default="medium")
    b = np.where(m["p25"].isna().values, "sin_cortes", b)
    return pd.Series(b, index=df.index)
