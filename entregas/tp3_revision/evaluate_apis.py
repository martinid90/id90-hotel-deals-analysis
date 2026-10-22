#!/usr/bin/env python3
"""Evalúa ambas APIs de TP3 con un set de casos común.

Uso típico:
  python entregas/tp3_revision/evaluate_apis.py \
    --cases entregas/tp3_revision/api_test_cases.csv \
    --g1-url http://localhost:8001/predict \
    --g2-url http://localhost:8002/evaluate \
    --out-dir entregas/tp3_revision
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests


@dataclass
class EvalStats:
    n_total: int
    n_scored: int
    coverage: float
    accuracy: float | None
    precision: float | None
    recall: float | None
    f1: float | None
    fpr: float | None


def to_int(x: Any, default: int) -> int:
    if pd.isna(x):
        return default
    return int(x)


def compute_nights(row: pd.Series) -> int:
    if "nights" in row and not pd.isna(row["nights"]):
        n = int(row["nights"])
        return max(n, 1)
    if "date_start" in row and "date_end" in row and pd.notna(row["date_start"]) and pd.notna(row["date_end"]):
        d1 = datetime.fromisoformat(str(row["date_start"]))
        d2 = datetime.fromisoformat(str(row["date_end"]))
        n = (d2 - d1).days
        return max(n, 1)
    return 1


def normalize_expected(v: Any) -> str | None:
    if pd.isna(v):
        return None
    s = str(v).strip().lower()
    if s in {"deal", "oferta", "si", "yes", "true", "1"}:
        return "deal"
    if s in {"no_deal", "normal", "no", "false", "0"}:
        return "no_deal"
    return None


def normalize_pred_g1(resp: dict[str, Any]) -> str | None:
    if resp is None:
        return None
    if str(resp.get("oferta", "")).upper() == "SI":
        return "deal"
    dec = str(resp.get("decision", "")).lower()
    if dec == "oferta":
        return "deal"
    if dec in {"normal", "sospechoso", "sin_soporte"}:
        return "no_deal"
    is_deal = resp.get("is_deal")
    if is_deal is True:
        return "deal"
    if is_deal is False:
        return "no_deal"
    return None


def normalize_pred_g2(resp: dict[str, Any]) -> str | None:
    if resp is None:
        return None
    dec = str(resp.get("decision", "")).lower()
    if dec == "deal":
        return "deal"
    if dec in {"no_deal", "insufficient_data", "invalid_price", "invalid_input"}:
        return "no_deal"
    is_deal = resp.get("is_deal")
    if is_deal is True:
        return "deal"
    if is_deal is False:
        return "no_deal"
    return None


def safe_post(url: str, payload: dict[str, Any], timeout: int = 20) -> tuple[int | None, dict[str, Any] | None, str | None]:
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        status = r.status_code
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text[:500]}
        return status, body, None
    except Exception as exc:
        return None, None, str(exc)


def calc_stats(df: pd.DataFrame, pred_col: str) -> EvalStats:
    base = df.copy()
    base = base[base["expected_norm"].isin(["deal", "no_deal"])].copy()
    n_total = len(base)
    scored = base[base[pred_col].isin(["deal", "no_deal"])].copy()
    n_scored = len(scored)
    coverage = n_scored / n_total if n_total else 0.0

    if n_scored == 0:
        return EvalStats(n_total, n_scored, coverage, None, None, None, None, None)

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

    return EvalStats(n_total, n_scored, coverage, acc, prec, rec, f1, fpr)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--g1-url", default="http://localhost:8001/predict")
    ap.add_argument("--g2-url", default="http://localhost:8002/evaluate")
    ap.add_argument("--out-dir", default="entregas/tp3_revision")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cases = pd.read_csv(args.cases)

    rows = []
    for _, r in cases.iterrows():
        case_id = r.get("case_id")
        city = r.get("city")
        state = r.get("state")
        country_code = str(r.get("country_code", "")).upper()
        country = r.get("country") if "country" in r else None
        date_start = str(r.get("date_start"))
        nights = compute_nights(r)
        adults = to_int(r.get("adults"), 2)
        kids = to_int(r.get("kids"), 0)
        rooms = to_int(r.get("rooms"), 1)
        price = float(r.get("price", r.get("price_input", 0.0)))

        # Grupo 1 payload
        g1_payload = {
            "city": city,
            "state": None if pd.isna(state) else state,
            "country": None if (country is None or pd.isna(country)) else country,
            "country_code": country_code.lower(),
            "date_start": date_start,
            "nights": nights,
            "adults": adults,
            "kids": kids,
            "rooms": rooms,
            "price": price,
        }

        # Grupo 2 payload (price_total)
        persons = max(adults + kids, 1)
        price_total = float(price * nights * rooms * persons)
        g2_payload = {
            "city": None if pd.isna(city) else city,
            "state": None if pd.isna(state) else state,
            "country": None if (country is None or pd.isna(country)) else country,
            "country_code": country_code,
            "date_start": date_start,
            "nights": nights,
            "adults": adults,
            "kids": kids,
            "rooms": rooms,
            "price_total": price_total,
        }

        g1_status, g1_body, g1_err = safe_post(args.g1_url, g1_payload)
        g2_status, g2_body, g2_err = safe_post(args.g2_url, g2_payload)

        row = {
            "case_id": case_id,
            "expected_label": r.get("expected_label"),
            "expected_norm": normalize_expected(r.get("expected_label")),
            "scenario_type": r.get("scenario_type"),
            "g1_status": g1_status,
            "g1_error": g1_err,
            "g1_pred_norm": normalize_pred_g1(g1_body) if g1_body else None,
            "g1_decision": None if not g1_body else g1_body.get("decision"),
            "g1_raw": json.dumps(g1_body, ensure_ascii=False) if g1_body else None,
            "g2_status": g2_status,
            "g2_error": g2_err,
            "g2_pred_norm": normalize_pred_g2(g2_body) if g2_body else None,
            "g2_decision": None if not g2_body else g2_body.get("decision"),
            "g2_raw": json.dumps(g2_body, ensure_ascii=False) if g2_body else None,
        }
        rows.append(row)

    res = pd.DataFrame(rows)

    g1_stats = calc_stats(res, "g1_pred_norm")
    g2_stats = calc_stats(res, "g2_pred_norm")

    metrics = pd.DataFrame([
        {
            "group": "grupo_01",
            "n_total_labeled": g1_stats.n_total,
            "n_scored": g1_stats.n_scored,
            "coverage": g1_stats.coverage,
            "accuracy": g1_stats.accuracy,
            "precision": g1_stats.precision,
            "recall": g1_stats.recall,
            "f1": g1_stats.f1,
            "fpr": g1_stats.fpr,
        },
        {
            "group": "grupo_02",
            "n_total_labeled": g2_stats.n_total,
            "n_scored": g2_stats.n_scored,
            "coverage": g2_stats.coverage,
            "accuracy": g2_stats.accuracy,
            "precision": g2_stats.precision,
            "recall": g2_stats.recall,
            "f1": g2_stats.f1,
            "fpr": g2_stats.fpr,
        },
    ])

    res.to_csv(out_dir / "api_results_comparativo.csv", index=False)
    metrics.to_csv(out_dir / "comparativo_metricas.csv", index=False)

    print("OK: resultados guardados en")
    print(f"- {out_dir / 'api_results_comparativo.csv'}")
    print(f"- {out_dir / 'comparativo_metricas.csv'}")
    print("\nMétricas:")
    print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
