"""Baseline histórico por contexto con cascada de fallback jerárquica.

Para cada nivel de la cascada se guardan estadísticos de price_std. Al
consultar, cada búsqueda toma el nivel más específico cuyo soporte
(`n_records`, búsquedas independientes) alcanza MIN_SUPPORT. Si ninguno
alcanza, queda en NO_SUPPORT_LEVEL y el sistema no decide.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import config

STAT_COLS = ["n_records", "demand_weight", "median", "mean", "std", "mean_log", "std_log", "p10"]
KEY_DTYPES = {"destination_final": str, "country_code": str, "stay_duration": str,
              "month": "int64", "week_in_month": "int64"}


def _cast_keys(df, keys):
    out = df[keys].copy()
    for k in keys:
        out[k] = out[k].astype(KEY_DTYPES[k]) if KEY_DTYPES[k] != str else out[k].astype("object")
    return out


class CascadeBaseline:
    def __init__(self, levels=None, min_support=config.MIN_SUPPORT, support_col=config.SUPPORT_COLUMN):
        self.levels = levels or config.CASCADE_LEVELS
        self.min_support = min_support
        self.support_col = support_col
        self.tables_ = {}

    def fit(self, df):
        for name, keys in self.levels:
            sub = df.dropna(subset=keys)
            g = sub.groupby(keys, observed=True)
            t = g.agg(
                n_records=("price_std", "size"),
                demand_weight=("count_repeated", "sum"),
                median=("price_std", "median"),
                mean=("price_std", "mean"),
                std=("price_std", "std"),
                mean_log=("log_price", "mean"),
                std_log=("log_price", "std"),
            )
            t["p10"] = g["price_std"].quantile(0.10)
            t = t.reset_index()
            self.tables_[name] = t
        return self

    def lookup(self, df):
        """Devuelve un DataFrame alineado con df: base_level + base_<stat>."""
        out = pd.DataFrame(index=df.index)
        out["base_level"] = config.NO_SUPPORT_LEVEL
        for c in STAT_COLS:
            out[f"base_{c}"] = np.nan
        pending = pd.Series(True, index=df.index)
        for name, keys in self.levels:
            if not pending.any():
                break
            t = self.tables_[name]
            t = t[t[self.support_col] >= self.min_support]
            cand = df.loc[pending].dropna(subset=keys)
            if cand.empty or t.empty:
                continue
            left = _cast_keys(cand, keys)
            left["_idx"] = cand.index
            m = left.merge(_cast_keys(t, keys).join(t[STAT_COLS]), on=keys, how="inner")
            if m.empty:
                continue
            idx = m["_idx"].values
            out.loc[idx, "base_level"] = name
            for c in STAT_COLS:
                out.loc[idx, f"base_{c}"] = m[c].values
            pending.loc[idx] = False
        return out

    # ------------------------------------------------------------------
    def save(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        meta = {"min_support": self.min_support, "support_col": self.support_col,
                "levels": [[n, k] for n, k in self.levels]}
        for name, keys in self.levels:
            t = self.tables_[name]
            # Para servir solo hacen falta las celdas con soporte suficiente
            t = t[t[self.support_col] >= self.min_support]
            t.to_csv(directory / f"{name}.csv.gz", index=False)
        (directory / "cascade_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, directory):
        directory = Path(directory)
        meta = json.loads((directory / "cascade_meta.json").read_text(encoding="utf-8"))
        obj = cls([(n, k) for n, k in meta["levels"]], meta["min_support"], meta["support_col"])
        for name, keys in obj.levels:
            obj.tables_[name] = pd.read_csv(directory / f"{name}.csv.gz",
                                            dtype={k: KEY_DTYPES[k] for k in keys})
        return obj
