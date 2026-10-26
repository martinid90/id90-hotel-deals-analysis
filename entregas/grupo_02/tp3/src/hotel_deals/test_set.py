"""Construcción del test set compartido (formato de query de la API).

Tres bloques, todos tomados del período de TEST (2025), nunca de train:
  1. real:      búsquedas reales estratificadas por tipo de destino x estadía x etiqueta.
  2. sintetico: búsquedas reales con precio reemplazado por factor x mediana del
                mercado realizado (0.3 ... 1.5).
  3. borde:     casos armados a mano para verificar fallback y validaciones.
"""

import numpy as np
import pandas as pd

from . import config

SYNTHETIC_FACTORS = [0.3, 0.4, 0.5, 0.7, 0.85, 1.0, 1.3, 1.5]
SEARCH_KEY = ["country_code", "state", "city", "date_start", "nights", "number_of_adults",
              "number_of_kids", "number_of_rooms", "avg_price_average"]


def destination_tier(df, train):
    """top50 / medio (51-500) / cola / sin_mapeo, por volumen de búsquedas en train."""
    rank = train.loc[train["is_mapped"], "destination_final"].value_counts().rank(ascending=False, method="first")
    r = df["destination_final"].map(rank)
    tier = np.where(r <= 50, "top50", np.where(r <= 500, "medio", "cola"))
    return pd.Series(np.where(df["is_mapped"], tier, "sin_mapeo"), index=df.index)


def _to_query(df, price_total):
    return pd.DataFrame({
        "city": df["city"].values, "state": df["state"].values, "country": df["country"].values,
        "country_code": df["country_code"].values,
        "date_start": pd.to_datetime(df["date_start"]).dt.strftime("%Y-%m-%d").values,
        "nights": df["nights"].values, "adults": df["number_of_adults"].values,
        "kids": df["number_of_kids"].astype(int).values, "rooms": df["number_of_rooms"].values,
        "price_total": np.round(np.asarray(price_total, dtype=float), 2),
    })


def build_real(test, per_stratum=150, seed=config.SEED):
    lab = test[test["is_deal"].notna()].drop_duplicates(SEARCH_KEY)
    strata = ["tier", "stay_duration", "is_deal"]
    sample = (lab.groupby(strata, group_keys=False)
              .apply(lambda g: g.sample(min(len(g), per_stratum), random_state=seed)))
    q = _to_query(sample, sample["avg_price_average"])
    q["case_type"] = "real"
    q["expected_is_deal"] = sample["is_deal"].values
    q["expected_decision"] = np.where(sample["is_deal"].values == 1, "deal", "no_deal")
    q["price_factor"] = np.nan
    q["tier"] = sample["tier"].values
    return q


def build_synthetic(test, n_base=300, seed=config.SEED):
    lab = test[test["is_deal"].notna()].drop_duplicates(SEARCH_KEY)
    base = (lab.groupby("tier", group_keys=False)
            .apply(lambda g: g.sample(min(len(g), n_base // 4), random_state=seed)))
    persons = base["number_of_adults"] + base["number_of_kids"]
    mult = (base["nights"] * base["number_of_rooms"] * persons).values
    std_log = np.maximum(base["oracle_base_std_log"].fillna(0).values, config.MIN_STD_LOG)
    blocks, internal = [], []
    for f in SYNTHETIC_FACTORS:
        p_std = f * base["oracle_base_median"].values
        z_log = (np.log(p_std) - base["oracle_base_mean_log"].values) / std_log
        # Verdad = misma definición de oferta aplicada al precio sintético
        truth = ((z_log < config.Z_LOG_THRESHOLD) & (1 - f >= config.MIN_DISCOUNT)).astype(float)
        q = _to_query(base, p_std * mult)
        q["case_type"] = "sintetico"
        q["expected_is_deal"] = truth
        q["expected_decision"] = np.where(truth == 1, "deal", "no_deal")
        q["price_factor"] = f
        q["tier"] = base["tier"].values
        blocks.append(q)
        b = base.copy()
        b["price_std"] = p_std
        b["log_price"] = np.log(p_std)
        b["is_deal"] = truth
        b["price_factor"] = f
        internal.append(b)
    return pd.concat(blocks, ignore_index=True), pd.concat(internal, ignore_index=True)


def build_edge_cases(train):
    """Casos borde con decisión esperada fija."""
    top = train[train["is_mapped"]].groupby(["destination_final"]).size().idxmax()
    ex = train[train["destination_final"] == top].iloc[0]
    unm = (train[~train["is_mapped"] & train["city"].notna()]
           .groupby(["country_code", "state", "city"], dropna=False).size().sort_values().index[-1])
    rows = [
        # (descripción, city, state, country, country_code, date, nights, adults, kids, rooms, price, esperado)
        ("Destino top, precio 80% bajo la mediana", ex["city"], ex["state"], ex["country"], ex["country_code"],
         "2025-07-10", 3, 2, 0, 1, None, "deal"),
        ("Destino top, precio 3x la mediana", ex["city"], ex["state"], ex["country"], ex["country_code"],
         "2025-07-10", 3, 2, 0, 1, None, "no_deal"),
        ("Ciudad inexistente en país conocido -> fallback país", "Ciudad Inventada", None, ex["country"],
         ex["country_code"], "2025-07-10", 3, 2, 0, 1, 300.0, "deal|no_deal"),
        ("Ciudad nula -> fallback país", None, None, ex["country"], ex["country_code"],
         "2025-03-05", 2, 1, 0, 1, 150.0, "deal|no_deal"),
        ("País inexistente -> sin soporte", "Atlantis", None, "Atlantida", "ZZ",
         "2025-07-10", 3, 2, 0, 1, 300.0, "insufficient_data"),
        ("Ciudad sin mapeo con historia propia", unm[2], unm[1], None, unm[0],
         "2025-05-14", 2, 2, 0, 1, 200.0, "deal|no_deal"),
        ("Precio absurdo (< 1 USD por persona-noche)", ex["city"], ex["state"], ex["country"], ex["country_code"],
         "2025-07-10", 3, 2, 0, 1, 3.0, "invalid_price"),
        ("Noches = 0", ex["city"], ex["state"], ex["country"], ex["country_code"],
         "2025-07-10", 0, 2, 0, 1, 300.0, "invalid_input"),
        ("Noches = 45 (fuera de rango)", ex["city"], ex["state"], ex["country"], ex["country_code"],
         "2025-07-10", 45, 2, 0, 1, 3000.0, "invalid_input"),
        ("Grupo grande: 6 adultos, 2 niños, 3 hab, 7 noches", ex["city"], ex["state"], ex["country"],
         ex["country_code"], "2025-12-20", 7, 6, 2, 3, 9000.0, "deal|no_deal"),
        ("Nombre en minúsculas y sin acentos", str(ex["city"]).lower(), ex["state"], ex["country"],
         ex["country_code"], "2025-07-10", 3, 2, 0, 1, 400.0, "deal|no_deal"),
    ]
    q = pd.DataFrame(rows, columns=["descripcion", "city", "state", "country", "country_code", "date_start",
                                    "nights", "adults", "kids", "rooms", "price_total", "expected_decision"])
    q["case_type"] = "borde"
    q["expected_is_deal"] = np.nan
    q["price_factor"] = np.nan
    q["tier"] = "borde"
    return q


def fill_edge_prices(edge, detector):
    """Completa los precios relativos (deal / caro) usando la mediana que sirve la API."""
    probe = detector.evaluate_frame(edge.assign(price_total=edge["price_total"].fillna(100.0)))
    mult = edge["nights"] * edge["rooms"] * (edge["adults"] + edge["kids"])
    for i, factor in [(0, 0.2), (1, 3.0)]:
        edge.loc[i, "price_total"] = round(float(probe.loc[i, "baseline_median"] * factor * mult[i]), 2)
    return edge
