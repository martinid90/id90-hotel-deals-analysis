"""Métricas, elección de umbral en validación y análisis de errores.

Convención: si un modelo no puede decidir (sin_soporte) cuenta como "no oferta"
para precisión/recall (es lo que vería el usuario), y además se reporta la cobertura.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

LABELED = ["oferta_clara", "no_oferta"]


def _counts(y: np.ndarray, p: np.ndarray) -> dict:
    tp = int(((p == 1) & (y == 1)).sum()); fp = int(((p == 1) & (y == 0)).sum())
    fn = int(((p == 0) & (y == 1)).sum()); tn = int(((p == 0) & (y == 0)).sum())
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def _from_counts(c: dict) -> dict:
    tp, fp, fn, tn = c["tp"], c["fp"], c["fn"], c["tn"]
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    acc = (tp + tn) / max(tp + fp + fn + tn, 1)
    return {"precision": prec, "recall": rec, "f1": f1, "fpr": fpr, "accuracy": acc}


def metrics(cases: pd.DataFrame, pred: pd.DataFrame) -> dict:
    lab = cases["tipo"].isin(LABELED).values
    y = cases["label"].values[lab].astype(int)
    p = pred["is_deal"].values[lab].astype(int)
    out = _from_counts(_counts(y, p))
    out["cobertura"] = float(pred["has_support"].values[lab].mean())
    real = (cases["tipo"] == "real").values
    out["cobertura_reales"] = float(pred["has_support"].values[real].mean())
    out["tasa_alerta_reales"] = float(pred["is_deal"].values[real].mean())
    err = (cases["tipo"] == "error_carga").values
    out["error_carga_como_oferta"] = float(pred["is_deal"].values[err].mean())
    out["n_etiquetados"] = int(lab.sum())
    return out


def metrics_weighted(cases: pd.DataFrame, pred: pd.DataFrame) -> dict:
    """Mismas métricas pero cada caso pesa según su demanda (`count_repeated`).
    Responde: ¿cómo le va al modelo en las búsquedas que más se repiten?
    Las variantes de un ancla heredan el peso del ancla."""
    w_all = cases["count_repeated"].astype(float).values
    lab = cases["tipo"].isin(LABELED).values
    y = cases["label"].values[lab].astype(int)
    p = pred["is_deal"].values[lab].astype(int)
    w = w_all[lab]
    c = {"tp": w[(p == 1) & (y == 1)].sum(), "fp": w[(p == 1) & (y == 0)].sum(),
         "fn": w[(p == 0) & (y == 1)].sum(), "tn": w[(p == 0) & (y == 0)].sum()}
    out = {f"{k}_pond": v for k, v in _from_counts(c).items()}
    real = (cases["tipo"] == "real").values
    wr = w_all[real]
    out["tasa_alerta_reales_pond"] = float((wr * pred["is_deal"].values[real]).sum() / wr.sum())
    out["cobertura_reales_pond"] = float((wr * pred["has_support"].values[real]).sum() / wr.sum())
    return out


def bootstrap_ci(cases: pd.DataFrame, pred: pd.DataFrame, n_boot: int = 1000, seed: int = config.SEED) -> dict:
    """IC 95% re-muestreando ANCLAS (todas las variantes de un ancla salen juntas → no se
    subestima la incertidumbre por tener 9 versiones del mismo precio)."""
    lab = cases["tipo"].isin(LABELED)
    d = pd.DataFrame({"a": cases.loc[lab, "anchor_id"].values, "y": cases.loc[lab, "label"].astype(int).values,
                      "p": pred.loc[lab, "is_deal"].astype(int).values})
    d["tp"] = (d.p == 1) & (d.y == 1); d["fp"] = (d.p == 1) & (d.y == 0)
    d["fn"] = (d.p == 0) & (d.y == 1); d["tn"] = (d.p == 0) & (d.y == 0)
    per = d.groupby("a")[["tp", "fp", "fn", "tn"]].sum().values
    rng = np.random.default_rng(seed)
    res = {k: [] for k in ["precision", "recall", "f1", "fpr"]}
    for _ in range(n_boot):
        s = per[rng.integers(0, len(per), len(per))].sum(axis=0)
        m = _from_counts({"tp": s[0], "fp": s[1], "fn": s[2], "tn": s[3]})
        for k in res:
            res[k].append(m[k])
    return {f"{k}_ic95": f"[{np.percentile(v, 2.5):.3f}, {np.percentile(v, 97.5):.3f}]" for k, v in res.items()}


def tune(model, val: pd.DataFrame) -> tuple[object, pd.DataFrame]:
    """Prueba cada valor de la grilla en VALIDACIÓN y elige el de mayor F1 entre los que no marcan
    más del 10% de los precios reales como oferta (restricción de producto)."""
    rows = []
    for v in model.grid:
        m = metrics(val, model.predict(val, v))
        rows.append({"modelo": model.name, "param": model.param_name, "valor": v, **m})
    g = pd.DataFrame(rows)
    ok = g[g["tasa_alerta_reales"] <= config.MAX_ALERT_RATE]
    best = (ok if len(ok) else g.nsmallest(1, "tasa_alerta_reales")).sort_values("f1", ascending=False).iloc[0]
    g["elegido"] = g["valor"] == best["valor"]
    return best["valor"], g


def detection_curve(cases: pd.DataFrame, pred: pd.DataFrame, model_name: str) -> pd.DataFrame:
    c = cases["tipo"] != "real"
    d = pd.DataFrame({"factor": cases.loc[c, "factor"], "oferta": pred.loc[c, "is_deal"],
                      "sospechoso": pred.loc[c, "decision"].eq("sospechoso")})
    out = d.groupby("factor").mean().reset_index()
    out["modelo"] = model_name
    out["variacion_pct"] = ((out["factor"] - 1) * 100).round().astype(int)
    return out


def error_slices(cases: pd.DataFrame, pred: pd.DataFrame, model_name: str) -> pd.DataFrame:
    """Recall (sobre ofertas claras) y tasa de falsos positivos (sobre no-ofertas) por segmento."""
    lab = cases["tipo"].isin(LABELED)
    d = cases.loc[lab, ["label", "tier_destino", "nivel_precio_mercado", "trimestre", "is_mapped"]].copy()
    d["nivel_contexto"] = pred.loc[lab, "level"].values
    d["ocupacion"] = np.select([cases.loc[lab, "pax_per_room"] <= 1, cases.loc[lab, "pax_per_room"] <= 2],
                               ["1_pax_hab", "2_pax_hab"], default="3+_pax_hab")
    d["noches"] = pd.cut(cases.loc[lab, "nights"], [0, 1, 3, 7, 100], labels=["1", "2-3", "4-7", "8+"]).astype(str)
    d["pred"] = pred.loc[lab, "is_deal"].values
    rows = []
    for dim in ["tier_destino", "nivel_precio_mercado", "trimestre", "is_mapped", "nivel_contexto", "ocupacion", "noches"]:
        for val, g in d.groupby(dim):
            pos, neg = g[g.label == 1], g[g.label == 0]
            rows.append({"modelo": model_name, "dimension": dim, "segmento": str(val),
                         "n_anclas": len(pos) // len(config.FACTORS_POS) if len(pos) else len(neg) // len(config.FACTORS_NEG),
                         "recall": pos["pred"].mean() if len(pos) else np.nan,
                         "fpr": neg["pred"].mean() if len(neg) else np.nan})
    return pd.DataFrame(rows)
