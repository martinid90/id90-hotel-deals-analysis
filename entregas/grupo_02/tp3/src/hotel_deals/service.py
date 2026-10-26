"""Servicio de detección: carga artefactos y evalúa queries en formato API.

Es el mismo código que usa la API, el test set compartido y los tests.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import config
from .baselines import CascadeBaseline
from .data import compute_price_std, stay_duration, week_in_month
from .detectors import scores
from .geo import DestinationMapper

QUERY_FIELDS = ["city", "state", "country", "country_code", "date_start", "nights",
                "adults", "kids", "rooms", "price_total"]


class DealDetector:
    def __init__(self, artifacts_dir=None, mapping_file=None):
        artifacts_dir = Path(artifacts_dir or config.default_artifacts_dir())
        self.params = json.loads((artifacts_dir / "params.json").read_text(encoding="utf-8"))
        self.cascade = CascadeBaseline.load(artifacts_dir / "baselines")
        self.mapper = DestinationMapper.from_file(mapping_file)
        self.cap = self.params["winsor_cap"]
        self.floor = self.params["price_std_floor"]
        self.z_thr = self.params["z_log_threshold"]
        self.min_disc = self.params["min_discount"]

    def evaluate_frame(self, q):
        """q: DataFrame con QUERY_FIELDS. Devuelve un DataFrame de respuestas."""
        q = q.copy()
        for c in ["city", "state", "country", "country_code"]:
            if c not in q.columns:
                q[c] = None
        q["kids"] = q.get("kids", 0)
        q["kids"] = q["kids"].fillna(0)
        q["date_start"] = pd.to_datetime(q["date_start"])

        valid = (q["nights"].between(1, config.MAX_NIGHTS) & (q["rooms"] >= 1)
                 & ((q["adults"] + q["kids"]) >= 1) & (q["price_total"] > 0))
        price_std = pd.Series(np.nan, index=q.index)
        price_std[valid] = compute_price_std(q.loc[valid, "price_total"], q.loc[valid, "nights"],
                                             q.loc[valid, "rooms"], q.loc[valid, "adults"],
                                             q.loc[valid, "kids"])
        below_floor = price_std < self.floor

        ctx = self.mapper.transform(q[["city", "state", "country", "country_code"]])
        ctx["month"] = q["date_start"].dt.month
        ctx["week_in_month"] = week_in_month(q["date_start"].dt.day.values)
        ctx["stay_duration"] = stay_duration(q["nights"].fillna(1).values)

        base = self.cascade.lookup(ctx)
        p = price_std.clip(lower=self.floor, upper=self.cap).fillna(self.floor)
        s = scores(p.values, base)
        is_deal = (s["z_log"] < self.z_thr) & (s["discount"] >= self.min_disc)
        no_support = base["base_level"].eq(config.NO_SUPPORT_LEVEL)

        decision = np.where(is_deal, "deal", "no_deal").astype(object)
        decision[no_support.values] = "insufficient_data"
        decision[below_floor.values] = "invalid_price"
        decision[~valid.values] = "invalid_input"

        out = pd.DataFrame({
            "decision": decision,
            "is_deal": pd.Series(decision == "deal", index=q.index).where(
                pd.Series(np.isin(decision, ["deal", "no_deal"]), index=q.index)),
            "price_std": price_std.round(4),
            "baseline_median": base["base_median"].round(4),
            "discount": s["discount"].round(4),
            "z_log": s["z_log"].round(4),
            "baseline_level": base["base_level"],
            "baseline_n_records": base["base_n_records"],
            "destination_final": ctx["destination_final"],
            "destination_name": ctx["destination_name"],
            "is_mapped": ctx["is_mapped"],
        }, index=q.index)
        undecided = ~np.isin(decision, ["deal", "no_deal"])
        out.loc[undecided, ["discount", "z_log"]] = np.nan
        out["explanation"] = [self._explain(r) for r in out.itertuples()]
        return out

    def _explain(self, r):
        """Frase legible que justifica la decisión con los números del contexto."""
        if r.decision == "invalid_input":
            return "Búsqueda inválida: las noches deben estar entre 1 y 30, con al menos 1 habitación y 1 persona."
        if r.decision == "invalid_price":
            return (f"Precio inválido: {r.price_std:.2f} USD por habitación-noche-persona está debajo del piso de "
                    f"{self.floor:.0f} USD, probablemente es un error de dato.")
        if r.decision == "insufficient_data":
            return (f"Sin datos suficientes: ningún nivel de la cascada tiene {self.params['min_support']} "
                    "búsquedas históricas para este destino y país.")
        ctx = (f"la mediana de {config.LEVEL_LABELS.get(r.baseline_level, r.baseline_level)} "
               f"({r.baseline_median:.2f} USD, {r.baseline_n_records:.0f} búsquedas)")
        if r.decision == "deal":
            return (f"Oferta: {r.price_std:.2f} USD por habitación-noche-persona está {r.discount:.0%} debajo de "
                    f"{ctx} y su z_log es {r.z_log:.2f} (umbral {self.z_thr:g}).")
        if r.z_log >= self.z_thr:
            motivo = f"su z_log es {r.z_log:.2f} y no llega al umbral {self.z_thr:g}"
        else:
            motivo = f"el descuento no llega al {self.min_disc:.0%} exigido"
        if r.discount >= 0:
            return (f"No es oferta: {r.price_std:.2f} USD por habitación-noche-persona está {r.discount:.0%} debajo "
                    f"de {ctx}, pero {motivo}.")
        return (f"No es oferta: {r.price_std:.2f} USD por habitación-noche-persona está {-r.discount:.0%} encima "
                f"de {ctx}.")

    def evaluate(self, query):
        res = self.evaluate_frame(pd.DataFrame([query])).iloc[0].to_dict()
        clean = {}
        for k, v in res.items():
            if isinstance(v, (float, np.floating)) and np.isnan(v):
                clean[k] = None
            elif isinstance(v, np.generic):
                clean[k] = v.item()
            elif v is pd.NA:
                clean[k] = None
            else:
                clean[k] = v
        return clean
