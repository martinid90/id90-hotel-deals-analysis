"""Diseño del set de validación y del set de test.

Separación (sin fugas):
  * train  = búsquedas con check-in en 2024. Es lo ÚNICO que ven los modelos (referencias,
             cortes de price_bucket, Isolation Forest, piso de precio).
  * 2025 se divide en tres pools DISJUNTOS por grupo (destino × fecha de check-in), así una
    misma fecha-destino nunca aparece en dos pools:
      - mercado (40%): solo sirve para construir la "verdad" (mediana de mercado 2025 por
                       destino × mes) con la que se eligen las anclas. Ningún modelo la ve.
      - val (30%):     se usa para elegir el umbral de cada modelo.
      - test (30%):    se usa una sola vez, al final, para comparar.

Casos de cada set:
  * controlados: "anclas" = búsquedas reales cuyo precio está a ±10% de la mediana de mercado
    2025 de su contexto (o sea, precios normales). A cada ancla se le aplican factores:
      0,40 0,50 0,60 0,70 → oferta clara (etiqueta 1)
      0,80 0,90           → zona gris (sin etiqueta, solo curva de detección)
      1,00 1,10 1,20 1,30 1,50 → no oferta (etiqueta 0)
      0,10                → error de carga (se espera 'sospechoso', no 'oferta')
    Las anclas se estratifican por volumen del destino, trimestre y nivel de precio del mercado.
  * reales: muestra aleatoria simple del pool, sin tocar, para medir cobertura y volumen de alertas.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from . import config
from .references import assign_bucket, fit_bucket_cuts

EXPORT_COLS = [
    "case_id", "anchor_id", "search_id", "tipo", "factor", "label",
    "country_code", "country", "state", "city", "cc", "destination_final", "destination_name", "is_mapped", "match_level",
    "date_start", "date_end", "nights", "number_of_adults", "number_of_kids", "number_of_rooms", "persons", "pax_per_room", "count_repeated",
    "month", "week_in_month", "price_original", "price", "log_price", "price_bucket_train",
    "med_mercado_2025", "nivel_verdad", "tier_destino", "nivel_precio_mercado", "trimestre",
]


def _hash_unit(s: pd.Series) -> np.ndarray:
    """Número en [0,1) determinístico a partir de un texto (para asignar pools sin azar no reproducible)."""
    return np.array([int(hashlib.md5(v.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF for v in s])


def split_2025_pools(df25: pd.DataFrame) -> pd.Series:
    group = df25["destination_final"].astype(str) + "|" + df25["date_start"].dt.strftime("%Y-%m-%d")
    u = _hash_unit(group)
    a, b = config.POOL_SHARES["mercado"], config.POOL_SHARES["mercado"] + config.POOL_SHARES["val"]
    return pd.Series(np.select([u < a, u < b], ["mercado", "val"], default="test"), index=df25.index)


def market_table(mercado: pd.DataFrame) -> pd.DataFrame:
    """Mediana de mercado 2025 ("verdad" para elegir anclas), jerárquica para cubrir destinos chicos:
    destino × mes → destino × trimestre → destino (cada una con >= MIN_SUPPORT búsquedas del pool mercado).
    Devuelve una fila por destino × mes posible."""
    m = mercado.assign(trimestre=(mercado["month"] - 1) // 3 + 1)
    out = None
    for nivel, keys in [("destino_mes", ["destination_final", "month"]),
                        ("destino_trimestre", ["destination_final", "trimestre"]),
                        ("destino", ["destination_final"])]:
        g = m.groupby(keys)["price"]
        t = pd.concat([g.size().rename("n_mercado"), g.median().rename("med_mercado_2025")], axis=1).reset_index()
        t = t[t["n_mercado"] >= config.MIN_SUPPORT].assign(nivel_verdad=nivel)
        grid = pd.DataFrame({"destination_final": m["destination_final"].unique()}).merge(
            pd.DataFrame({"month": range(1, 13)}), how="cross")
        grid["trimestre"] = (grid["month"] - 1) // 3 + 1
        t = grid.merge(t, on=keys, how="inner")[["destination_final", "month", "n_mercado", "med_mercado_2025", "nivel_verdad"]]
        out = t if out is None else pd.concat([out, t[~t.set_index(["destination_final", "month"]).index.isin(
            out.set_index(["destination_final", "month"]).index)]])
    return out.reset_index(drop=True)


def _tiers(train: pd.DataFrame) -> pd.DataFrame:
    vol = train["destination_final"].value_counts()
    rank = vol.rank(ascending=False, method="first")
    tier = pd.Series(np.select([rank <= 50, rank <= 500], ["top50", "51-500"], default="cola"), index=vol.index)
    tier[vol < config.MIN_SUPPORT] = "poco_soporte_2024"
    return tier.rename("tier_destino").rename_axis("destination_final").reset_index()


def _annotate(pool: pd.DataFrame, mkt: pd.DataFrame, tiers: pd.DataFrame, price_cuts: list[float]) -> pd.DataFrame:
    x = pool.merge(mkt[["destination_final", "month", "med_mercado_2025", "nivel_verdad"]], on=["destination_final", "month"], how="left")
    x = x.merge(tiers, on="destination_final", how="left")
    x["tier_destino"] = x["tier_destino"].fillna("nuevo_en_2025")
    x["nivel_precio_mercado"] = pd.cut(x["med_mercado_2025"], bins=[-np.inf] + price_cuts + [np.inf],
                                       labels=["muy_barato", "barato", "medio", "caro", "muy_caro"]).astype(str)
    x["trimestre"] = "T" + ((x["month"] - 1) // 3 + 1).astype(str)
    return x


def _sample_anchors(x: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    cand = x[x["med_mercado_2025"].notna() & ((x["price"] / x["med_mercado_2025"] - 1).abs() <= config.ANCHOR_TOL)]
    # evitar repeticiones: como mucho un ancla por destino × fecha × ocupación
    cand = cand.drop_duplicates(["destination_final", "date_start", "persons", "number_of_rooms"])
    strata = cand.groupby(["tier_destino", "trimestre", "nivel_precio_mercado"], observed=True)
    per = int(np.ceil(n / strata.ngroups))
    picked = strata.apply(lambda g: g.sample(min(per, len(g)), random_state=seed), include_groups=False)
    picked = picked.reset_index(level=[0, 1, 2]).reset_index(drop=True)
    if len(picked) > n:
        picked = picked.sample(n, random_state=seed)
    # si algún estrato no llegó, completar al azar con el resto
    if len(picked) < n:
        rest = cand[~cand["search_id"].isin(picked["search_id"])]
        picked = pd.concat([picked, rest.sample(min(n - len(picked), len(rest)), random_state=seed)])
    return picked.reset_index(drop=True)


def _variants(anchors: pd.DataFrame, prefix: str) -> pd.DataFrame:
    tipos = ([(f, "oferta_clara", 1.0) for f in config.FACTORS_POS]
             + [(f, "gris", np.nan) for f in config.FACTORS_GRIS]
             + [(f, "no_oferta", 0.0) for f in config.FACTORS_NEG]
             + [(f, "error_carga", np.nan) for f in config.FACTORS_ERROR])
    parts = []
    for f, tipo, label in tipos:
        v = anchors.copy()
        v["factor"], v["tipo"], v["label"] = f, tipo, label
        v["price"] = v["price_original"] * f
        parts.append(v)
    out = pd.concat(parts, ignore_index=True)
    out["log_price"] = np.log(out["price"])
    out["case_id"] = prefix + "_" + out["anchor_id"] + "_f" + out["factor"].map(lambda f: f"{f:.2f}")
    return out


def build_sets(train: pd.DataFrame, df25: pd.DataFrame) -> dict[str, pd.DataFrame]:
    df25 = df25.copy()
    df25["pool"] = split_2025_pools(df25)
    mkt = market_table(df25[df25["pool"] == "mercado"])
    price_cuts = list(mkt["med_mercado_2025"].quantile([0.2, 0.4, 0.6, 0.8]).values)
    tiers = _tiers(train)
    cuts = fit_bucket_cuts(train)  # solo train

    sets = {}
    for name, n_anchor, seed in [("val", config.N_ANCHORS_VAL, config.SEED), ("test", config.N_ANCHORS_TEST, config.SEED + 1)]:
        pool = _annotate(df25[df25["pool"] == name], mkt, tiers, price_cuts)
        pool["price_original"] = pool["price"]

        anchors = _sample_anchors(pool, n_anchor, seed)
        anchors["anchor_id"] = anchors["search_id"]
        controlled = _variants(anchors, name)

        reales = pool.sample(min(config.N_REALES, len(pool)), random_state=seed).copy()
        reales["anchor_id"] = reales["search_id"]
        reales["factor"], reales["tipo"], reales["label"] = 1.0, "real", np.nan
        reales["case_id"] = name + "_real_" + reales["search_id"]

        s = pd.concat([controlled, reales], ignore_index=True)
        # bucket con cortes de train sobre el precio FINAL (modificado): consistente con producción
        s["price_bucket_train"] = assign_bucket(s, cuts)
        s["date_start"] = s["date_start"].dt.strftime("%Y-%m-%d")
        s["date_end"] = s["date_end"].dt.strftime("%Y-%m-%d")
        sets[name] = s[EXPORT_COLS]
    sets["_pools"] = df25["pool"].value_counts().rename_axis("pool").reset_index()
    return sets


def load_set(path) -> pd.DataFrame:
    # keep_default_na=False: "NA" es Namibia, no un nulo
    s = pd.read_csv(path, dtype={"search_id": str, "anchor_id": str, "destination_final": str, "cc": str},
                    keep_default_na=False, na_values=[""])
    s["date_start"] = pd.to_datetime(s["date_start"])
    s["date_end"] = pd.to_datetime(s["date_end"])
    return s
