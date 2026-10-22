#!/usr/bin/env python3
"""Validación robusta TP3: genera benchmark ampliado y evalúa ambas APIs.

Ejemplos:
  python entregas/tp3_revision/robust_validation_tp3.py build \
    --historical data/datos_historicos_2025.csv \
    --out-cases entregas/tp3_revision/robust_test_cases.csv

  python entregas/tp3_revision/robust_validation_tp3.py eval \
    --cases entregas/tp3_revision/robust_test_cases.csv \
    --g1-url http://localhost:8001/predict \
    --g2-url http://localhost:8002/evaluate \
    --out-dir entregas/tp3_revision \
    --g2-price-mode multiply
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests


# -----------------------------
# Build robust test cases
# -----------------------------


def _normalize_text(s: pd.Series) -> pd.Series:
    return s.fillna("").astype(str).str.strip().str.lower()


def load_historical(path: Path) -> pd.DataFrame:
    cols = [
        "city",
        "state",
        "country",
        "country_code",
        "date_start",
        "date_end",
        "number_of_adults",
        "number_of_rooms",
        "number_of_kids",
        "nights",
        "avg_price_average",
    ]
    df = pd.read_csv(path, usecols=cols, low_memory=False)

    df["city"] = _normalize_text(df["city"])
    df["state"] = _normalize_text(df["state"])
    df["country"] = _normalize_text(df["country"])
    df["country_code"] = _normalize_text(df["country_code"])

    df["number_of_kids"] = df["number_of_kids"].fillna(0)
    df["persons"] = (df["number_of_adults"] + df["number_of_kids"]).clip(lower=1)

    valid = (
        df["nights"].between(1, 30)
        & (df["number_of_rooms"] >= 1)
        & (df["number_of_adults"] >= 1)
        & (df["avg_price_average"] > 0)
        & (df["avg_price_average"] < 50_000)
        & (df["country_code"].str.len() >= 2)
        & (df["city"] != "")
    )
    df = df[valid].copy()

    dt = pd.to_datetime(df["date_start"], errors="coerce")
    df = df[dt.notna()].copy()
    df["date_start"] = pd.to_datetime(df["date_start"])
    df["month"] = df["date_start"].dt.month

    df["stay_bucket"] = np.select(
        [df["nights"] <= 1, df["nights"].between(2, 3), df["nights"].between(4, 6)],
        ["1", "2_3", "4_6"],
        default="7_plus",
    )
    df["persons_bucket"] = np.select(
        [df["persons"] == 1, df["persons"] == 2, df["persons"].between(3, 4)],
        ["1", "2", "3_4"],
        default="5_plus",
    )
    return df


def build_cases(
    historical_csv: Path,
    out_cases: Path,
    n_anchors: int = 120,
    min_support: int = 30,
    seed: int = 42,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = load_historical(historical_csv)

    ctx_keys = ["country_code", "city", "state", "month", "stay_bucket", "persons_bucket"]
    stats = (
        df.groupby(ctx_keys, dropna=False)["avg_price_average"]
        .agg(ctx_n="size", ctx_median="median")
        .reset_index()
    )
    work = df.merge(stats, on=ctx_keys, how="left")
    work["ratio_to_ctx_median"] = work["avg_price_average"] / work["ctx_median"]

    # Anclas cercanas a mediana para controlar mejor etiquetas por construcción.
    anchors = work[
        (work["ctx_n"] >= min_support)
        & work["ratio_to_ctx_median"].between(0.9, 1.1)
    ].copy()

    if anchors.empty:
        raise RuntimeError("No hay anclas elegibles. Bajar min_support o ampliar datos.")

    top_countries = anchors["country_code"].value_counts().head(6).index.tolist()
    anchors["country_bin"] = np.where(anchors["country_code"].isin(top_countries), anchors["country_code"], "other")

    # Muestreo ponderado: favorece contextos de menor soporte para testear generalización.
    w = 1.0 / np.sqrt(anchors["ctx_n"].astype(float))
    w = w / w.sum()
    n_take = min(n_anchors, len(anchors))
    picked_idx = rng.choice(anchors.index.to_numpy(), size=n_take, replace=False, p=w.to_numpy())
    picked = anchors.loc[picked_idx].copy().reset_index(drop=True)

    factors = [0.55, 0.70, 0.85, 1.00, 1.15, 1.35]
    rows: list[dict[str, Any]] = []
    c = 1
    for _, r in picked.iterrows():
        d0 = pd.to_datetime(r["date_start"]).date()
        date_end = d0 + timedelta(days=int(r["nights"]))

        for f in factors:
            price = float(r["avg_price_average"] * f)
            if f <= 0.70:
                label = "deal"
                scen = "synthetic_deal"
            elif f >= 1.00:
                label = "no_deal"
                scen = "synthetic_no_deal"
            else:
                label = "borderline"
                scen = "synthetic_borderline"

            rows.append(
                {
                    "case_id": f"RB{c:05d}",
                    "city": r["city"],
                    "state": r["state"],
                    "country": r["country"],
                    "country_code": str(r["country_code"]).upper(),
                    "date_start": d0.isoformat(),
                    "date_end": date_end.isoformat(),
                    "nights": int(r["nights"]),
                    "adults": int(r["number_of_adults"]),
                    "kids": int(r["number_of_kids"]),
                    "rooms": int(r["number_of_rooms"]),
                    "price": round(price, 2),
                    "factor": f,
                    "scenario_type": scen,
                    "expected_label": label,
                    "ctx_support": int(r["ctx_n"]),
                    "ctx_median": round(float(r["ctx_median"]), 4),
                    "stay_bucket": r["stay_bucket"],
                    "persons_bucket": r["persons_bucket"],
                    "country_bin": r["country_bin"],
                    "notes": "Generated from 2025 anchor near context median",
                }
            )
            c += 1

    out = pd.DataFrame(rows)
    out_cases.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_cases, index=False)
    return out


# -----------------------------
# Evaluate APIs
# -----------------------------


def to_int(x: Any, default: int) -> int:
    try:
        if pd.isna(x):
            return default
    except Exception:
        pass
    return int(x)


def compute_nights(row: pd.Series) -> int:
    if "nights" in row and not pd.isna(row["nights"]):
        return max(int(row["nights"]), 1)
    d1 = datetime.fromisoformat(str(row["date_start"]))
    d2 = datetime.fromisoformat(str(row["date_end"]))
    return max((d2 - d1).days, 1)


def normalize_label(v: Any) -> str | None:
    if pd.isna(v):
        return None
    s = str(v).strip().lower()
    if s in {"deal", "oferta", "si", "yes", "true", "1"}:
        return "deal"
    if s in {"no_deal", "normal", "no", "false", "0"}:
        return "no_deal"
    return None


def normalize_pred_g1(resp: dict[str, Any] | None) -> str | None:
    if not resp:
        return None
    if str(resp.get("oferta", "")).upper() == "SI":
        return "deal"
    d = str(resp.get("decision", "")).lower()
    if d == "oferta":
        return "deal"
    if d in {"normal", "sospechoso", "sin_soporte"}:
        return "no_deal"
    b = resp.get("is_deal")
    if b is True:
        return "deal"
    if b is False:
        return "no_deal"
    return None


def normalize_pred_g2(resp: dict[str, Any] | None) -> str | None:
    if not resp:
        return None
    d = str(resp.get("decision", "")).lower()
    if d == "deal":
        return "deal"
    if d in {"no_deal", "insufficient_data", "invalid_price", "invalid_input"}:
        return "no_deal"
    b = resp.get("is_deal")
    if b is True:
        return "deal"
    if b is False:
        return "no_deal"
    return None


def safe_post(url: str, payload: dict[str, Any], timeout: int = 20) -> tuple[int | None, dict[str, Any] | None, str | None]:
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        st = r.status_code
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text[:400]}
        return st, body, None
    except Exception as exc:
        return None, None, str(exc)


@dataclass
class EvalStats:
    n_total: int
    n_scored: int
    coverage: float
    tp: int
    tn: int
    fp: int
    fn: int
    accuracy: float | None
    precision: float | None
    recall: float | None
    f1: float | None
    fpr: float | None


def calc_stats(df: pd.DataFrame, pred_col: str) -> EvalStats:
    base = df[df["expected_norm"].isin(["deal", "no_deal"])].copy()
    n_total = len(base)
    scored = base[base[pred_col].isin(["deal", "no_deal"])].copy()
    n_scored = len(scored)
    coverage = n_scored / n_total if n_total else 0.0

    if n_scored == 0:
        return EvalStats(n_total, n_scored, coverage, 0, 0, 0, 0, None, None, None, None, None)

    y = scored["expected_norm"]
    p = scored[pred_col]

    tp = int(((p == "deal") & (y == "deal")).sum())
    tn = int(((p == "no_deal") & (y == "no_deal")).sum())
    fp = int(((p == "deal") & (y == "no_deal")).sum())
    fn = int(((p == "no_deal") & (y == "deal")).sum())

    acc = (tp + tn) / n_scored if n_scored else None
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    f1 = (2 * prec * rec / (prec + rec)) if (prec is not None and rec is not None and (prec + rec) > 0) else None
    fpr = fp / (fp + tn) if (fp + tn) else None
    return EvalStats(n_total, n_scored, coverage, tp, tn, fp, fn, acc, prec, rec, f1, fpr)


def bootstrap_ci(df: pd.DataFrame, pred_col: str, metric: str, n_boot: int = 400, seed: int = 42) -> tuple[float | None, float | None]:
    scored = df[df["expected_norm"].isin(["deal", "no_deal"]) & df[pred_col].isin(["deal", "no_deal"])].copy()
    if scored.empty:
        return None, None
    rng = np.random.default_rng(seed)
    vals = []
    n = len(scored)
    for _ in range(n_boot):
        s = scored.iloc[rng.integers(0, n, size=n)]
        st = calc_stats(s, pred_col)
        vals.append(getattr(st, metric))
    vals = [v for v in vals if v is not None]
    if not vals:
        return None, None
    return float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))


def evaluate_cases(
    cases_csv: Path,
    out_dir: Path,
    g1_url: str,
    g2_url: str,
    g2_price_mode: str = "multiply",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cases = pd.read_csv(cases_csv)
    rows = []
    for _, r in cases.iterrows():
        city = r.get("city")
        state = r.get("state")
        country = r.get("country")
        cc = str(r.get("country_code", "")).strip().upper()
        date_start = str(r.get("date_start"))
        nights = compute_nights(r)
        adults = to_int(r.get("adults"), 2)
        kids = to_int(r.get("kids"), 0)
        rooms = to_int(r.get("rooms"), 1)
        price = float(r.get("price", 0.0))

        g1_payload = {
            "city": city,
            "state": None if pd.isna(state) else state,
            "country": None if pd.isna(country) else country,
            "country_code": cc.lower(),
            "date_start": date_start,
            "nights": nights,
            "adults": adults,
            "kids": kids,
            "rooms": rooms,
            "price": price,
        }

        persons = max(adults + kids, 1)
        if g2_price_mode == "multiply":
            price_total = price * nights * rooms * persons
        elif g2_price_mode == "direct":
            price_total = price
        else:
            raise ValueError("g2_price_mode debe ser multiply o direct")

        g2_payload = {
            "city": None if pd.isna(city) else city,
            "state": None if pd.isna(state) else state,
            "country": None if pd.isna(country) else country,
            "country_code": cc,
            "date_start": date_start,
            "nights": nights,
            "adults": adults,
            "kids": kids,
            "rooms": rooms,
            "price_total": float(price_total),
        }

        g1_status, g1_body, g1_err = safe_post(g1_url, g1_payload)
        g2_status, g2_body, g2_err = safe_post(g2_url, g2_payload)

        rows.append(
            {
                "case_id": r.get("case_id"),
                "scenario_type": r.get("scenario_type"),
                "expected_label": r.get("expected_label"),
                "expected_norm": normalize_label(r.get("expected_label")),
                "factor": r.get("factor"),
                "ctx_support": r.get("ctx_support"),
                "stay_bucket": r.get("stay_bucket"),
                "persons_bucket": r.get("persons_bucket"),
                "country_bin": r.get("country_bin"),
                "g1_status": g1_status,
                "g1_error": g1_err,
                "g1_pred_norm": normalize_pred_g1(g1_body),
                "g1_decision": None if not g1_body else g1_body.get("decision"),
                "g1_raw": json.dumps(g1_body, ensure_ascii=False) if g1_body else None,
                "g2_status": g2_status,
                "g2_error": g2_err,
                "g2_pred_norm": normalize_pred_g2(g2_body),
                "g2_decision": None if not g2_body else g2_body.get("decision"),
                "g2_raw": json.dumps(g2_body, ensure_ascii=False) if g2_body else None,
            }
        )

    res = pd.DataFrame(rows)

    g1 = calc_stats(res, "g1_pred_norm")
    g2 = calc_stats(res, "g2_pred_norm")

    metrics = []
    for name, st, col in [("grupo_01", g1, "g1_pred_norm"), ("grupo_02", g2, "g2_pred_norm")]:
        f1_l, f1_u = bootstrap_ci(res, col, "f1")
        rec_l, rec_u = bootstrap_ci(res, col, "recall")
        metrics.append(
            {
                "group": name,
                "g2_price_mode": g2_price_mode,
                "n_total_labeled": st.n_total,
                "n_scored": st.n_scored,
                "coverage": st.coverage,
                "tp": st.tp,
                "tn": st.tn,
                "fp": st.fp,
                "fn": st.fn,
                "accuracy": st.accuracy,
                "precision": st.precision,
                "recall": st.recall,
                "f1": st.f1,
                "fpr": st.fpr,
                "f1_ci_low": f1_l,
                "f1_ci_high": f1_u,
                "recall_ci_low": rec_l,
                "recall_ci_high": rec_u,
            }
        )
    metrics_df = pd.DataFrame(metrics)

    seg_rows = []
    for seg_col in ["scenario_type", "stay_bucket", "persons_bucket", "country_bin"]:
        for seg_val, seg_df in res.groupby(seg_col, dropna=False):
            for grp, pcol in [("grupo_01", "g1_pred_norm"), ("grupo_02", "g2_pred_norm")]:
                st = calc_stats(seg_df, pcol)
                seg_rows.append(
                    {
                        "group": grp,
                        "segment": seg_col,
                        "segment_value": seg_val,
                        "n_total_labeled": st.n_total,
                        "n_scored": st.n_scored,
                        "coverage": st.coverage,
                        "accuracy": st.accuracy,
                        "precision": st.precision,
                        "recall": st.recall,
                        "f1": st.f1,
                        "fpr": st.fpr,
                    }
                )
    seg_df = pd.DataFrame(seg_rows)

    out_dir.mkdir(parents=True, exist_ok=True)
    res.to_csv(out_dir / "robust_api_results.csv", index=False)
    metrics_df.to_csv(out_dir / "robust_metrics_global.csv", index=False)
    seg_df.to_csv(out_dir / "robust_metrics_by_segment.csv", index=False)
    return res, metrics_df, seg_df


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build")
    p_build.add_argument("--historical", default="data/datos_historicos_2025.csv")
    p_build.add_argument("--out-cases", default="entregas/tp3_revision/robust_test_cases.csv")
    p_build.add_argument("--n-anchors", type=int, default=120)
    p_build.add_argument("--min-support", type=int, default=30)
    p_build.add_argument("--seed", type=int, default=42)

    p_eval = sub.add_parser("eval")
    p_eval.add_argument("--cases", default="entregas/tp3_revision/robust_test_cases.csv")
    p_eval.add_argument("--g1-url", default="http://localhost:8001/predict")
    p_eval.add_argument("--g2-url", default="http://localhost:8002/evaluate")
    p_eval.add_argument("--out-dir", default="entregas/tp3_revision")
    p_eval.add_argument("--g2-price-mode", choices=["multiply", "direct"], default="multiply")

    args = parser.parse_args()

    if args.cmd == "build":
        out = build_cases(
            historical_csv=Path(args.historical),
            out_cases=Path(args.out_cases),
            n_anchors=args.n_anchors,
            min_support=args.min_support,
            seed=args.seed,
        )
        labeled = out[out["expected_label"].isin(["deal", "no_deal"])]
        print(f"OK build: {args.out_cases}")
        print(f"total_cases={len(out)} labeled_cases={len(labeled)}")
        print("scenario mix:")
        print(out["scenario_type"].value_counts().to_string())
        return

    if args.cmd == "eval":
        _, m, s = evaluate_cases(
            cases_csv=Path(args.cases),
            out_dir=Path(args.out_dir),
            g1_url=args.g1_url,
            g2_url=args.g2_url,
            g2_price_mode=args.g2_price_mode,
        )
        print("OK eval:")
        print(m.to_string(index=False))
        print(f"segment_rows={len(s)}")
        return


if __name__ == "__main__":
    main()
