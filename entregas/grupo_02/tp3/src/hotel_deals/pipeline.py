"""Pipeline de punta a punta del TP3.

    datos -> curación -> split temporal -> baselines (train) -> etiquetas de
    referencia -> detectores A..G -> métricas -> análisis de errores ->
    sensibilidad -> artefactos para la API -> test set compartido.

Todos los números del README y del reporte salen de los archivos que escribe
esta función en outputs/.
"""

import json
import logging
import time

import numpy as np
import pandas as pd

from . import config
from . import detectors as det
from . import test_set as ts
from .baselines import CascadeBaseline
from .data import WinsorCap, prepare
from .evaluation import classification_metrics, metrics_by_group, metrics_table
from .geo import DestinationMapper
from .ml import DealClassifier
from .service import DealDetector

log = logging.getLogger(__name__)


def _baseline_predictions(df, cascade, prefix=""):
    base = cascade.lookup(df)
    preds = {name: fn(df["price_std"].values, base) for name, fn in det.BASELINE_DETECTORS.items()}
    return preds, base


def price_bucket_from_train(train, df):
    """price_bucket SOLO para análisis de errores: umbrales p25/p75 por destino
    calculados en train (destinos no vistos usan los umbrales globales)."""
    q = train.groupby("destination_final")["price_std"].quantile([0.25, 0.75]).unstack()
    q = q[train.groupby("destination_final").size() >= config.MIN_SUPPORT]
    p25 = df["destination_final"].map(q[0.25]).fillna(train["price_std"].quantile(0.25))
    p75 = df["destination_final"].map(q[0.75]).fillna(train["price_std"].quantile(0.75))
    return pd.Series(np.where(df["price_std"] <= p25, "low", np.where(df["price_std"] >= p75, "high", "medium")),
                     index=df.index)


def sensitivity(train_raw, test_raw, label_test):
    """Sensibilidad del detector híbrido a soporte, contexto, umbrales y outliers.
    La etiqueta de referencia se mantiene fija salvo en el bloque de outliers."""
    rows = []
    winsor = WinsorCap().fit(train_raw)
    train, test = winsor.transform(train_raw), winsor.transform(test_raw)
    y = label_test

    def add(bloque, variante, pred, prevalence=None):
        m = classification_metrics(y if prevalence is None else prevalence[0], pred)
        m.update(bloque=bloque, variante=variante)
        rows.append(m)

    for ms in [10, 30, 50, 100]:
        cb = CascadeBaseline(min_support=ms).fit(train)
        add("soporte_minimo (n_records)", f">= {ms}", det.hybrid(test["price_std"].values, cb.lookup(test)))
    cb = CascadeBaseline(support_col="demand_weight").fit(train)
    add("unidad de soporte", "demand_weight >= 30", det.hybrid(test["price_std"].values, cb.lookup(test)))

    L = dict(config.CASCADE_LEVELS)
    variants = {
        "solo L1 (sin fallback)": ["L1_dest_mes_semana_estadia"],
        "cascada sin semana (L2..L6)": [k for k in L if k != "L1_dest_mes_semana_estadia"],
        "cascada sin nivel país (L1..L5)": [k for k in L if k != "L6_pais_mes_estadia"],
        "solo destino (L5)": ["L5_dest"],
        "cascada completa (L1..L6)": list(L),
    }
    for name, keys in variants.items():
        cb = CascadeBaseline(levels=[(k, L[k]) for k in keys]).fit(train)
        add("definición de contexto", name, det.hybrid(test["price_std"].values, cb.lookup(test)))

    cb = CascadeBaseline().fit(train)
    base = cb.lookup(test)
    for z in [-0.5, -0.75, -1.0, -1.25, -1.5]:
        add("umbral z_log (descuento >= 20%)", f"z_log < {z}", det.hybrid(test["price_std"].values, base, z_thr=z))
    for d in [0.10, 0.20, 0.30]:
        add("umbral descuento (z_log < -1)", f">= {int(d * 100)}%", det.hybrid(test["price_std"].values, base, min_disc=d))

    # Outliers: cambia el dato, así que se recalculan baseline Y etiqueta
    for q in [0.99, 0.995, 0.999, None]:
        w = WinsorCap(q).fit(train_raw)
        tr, te = w.transform(train_raw), w.transform(test_raw)
        lab = det.oracle_labels(te)["is_deal"]
        pred = det.hybrid(te["price_std"].values, CascadeBaseline().fit(tr).lookup(te))
        m = classification_metrics(lab, pred)
        m.update(bloque="winsorización (recalcula etiqueta)",
                 variante=f"p{q * 100:g} (cap {w.cap_:.0f} USD)" if q else "sin winsorizar")
        rows.append(m)

    cols = ["bloque", "variante", "precision", "recall", "f1", "fpr", "cobertura", "tasa_marcados", "prevalencia"]
    return pd.DataFrame(rows)[cols]


def run(source="sample", write=True, do_sensitivity=True, do_ml=True):
    t0 = time.time()
    out = config.output_dir(source)
    out.mkdir(parents=True, exist_ok=True)
    R = {"source": source}

    # 1. Datos ----------------------------------------------------------
    mapper = DestinationMapper.from_file()
    df, funnel = prepare(source, mapper)
    R["funnel"] = funnel
    train_raw = df[df["year"] == config.TRAIN_YEAR].copy()
    test_raw = df[df["year"] == config.TEST_YEAR].copy()
    log.info("train=%s test=%s", len(train_raw), len(test_raw))

    # 2. Outliers calibrados en train ------------------------------------
    winsor = WinsorCap().fit(train_raw)
    train, test = winsor.transform(train_raw), winsor.transform(test_raw)

    # 3. Baseline histórico y etiquetas de referencia ---------------------
    cascade = CascadeBaseline().fit(train)
    train = train.join(det.oracle_labels(train))
    test = test.join(det.oracle_labels(test))
    prevalence = float(train["is_deal"].mean())

    ev = test[test["is_deal"].notna()].copy()
    y = ev["is_deal"]
    preds, base = _baseline_predictions(ev, cascade)
    ev = ev.join(base)
    ev = ev.join(det.scores(ev["price_std"].values, base))
    preds = {"A_naive_aleatorio": det.random_naive(len(ev), prevalence, index=ev.index), **preds}
    # Variante post-hoc (surge de la sensibilidad): misma regla, cascada sin semana del mes
    cascade_nw = CascadeBaseline(levels=config.CASCADE_LEVELS[1:]).fit(train)
    preds["E2_hibrido_sin_semana_posthoc"] = det.hybrid(ev["price_std"].values, cascade_nw.lookup(ev))

    # 4. ML con features exógenas ------------------------------------------
    models = {}
    if do_ml:
        tr_lab = train[train["is_deal"].notna()]
        for kind, name in [("hgb", "F_ml_hist_gradient_boosting"), ("rf", "G_ml_random_forest")]:
            t = time.time()
            models[name] = DealClassifier(kind).fit(tr_lab, tr_lab["is_deal"])
            preds[name] = models[name].predict(ev)
            log.info("%s entrenado en %.0fs (umbral %.2f)", name, time.time() - t, models[name].threshold_)

    for name, p in preds.items():
        ev[f"pred_{name}"] = p
    metrics = metrics_table(y, preds)
    metrics_w = metrics_table(y, preds, weights=ev["count_repeated"])

    # 5. Split aleatorio (dentro de 2024), como control ---------------------
    rng = np.random.default_rng(config.SEED)
    is_te = rng.random(len(train)) < 0.2
    r_tr, r_te = train[~is_te], train[is_te & train["is_deal"].notna()]
    cb_r = CascadeBaseline().fit(r_tr)
    preds_r, _ = _baseline_predictions(r_te, cb_r)
    preds_r = {"A_naive_aleatorio": det.random_naive(len(r_te), prevalence, index=r_te.index), **preds_r}
    if do_ml:
        r_lab = r_tr[r_tr["is_deal"].notna()]
        preds_r["F_ml_hist_gradient_boosting"] = DealClassifier("hgb").fit(r_lab, r_lab["is_deal"]).predict(r_te)
    metrics_random = metrics_table(r_te["is_deal"], preds_r)

    # 6. Cobertura por nivel de cascada y análisis de errores ----------------
    ev["tier"] = ts.destination_tier(ev, train)
    ev["price_bucket"] = price_bucket_from_train(train, ev)
    ev["mapeo"] = np.where(ev["is_mapped"], "mapeado", "sin_mapeo")
    level_cov = (test.join(cascade.lookup(test))["base_level"].value_counts(normalize=True)
                 .rename("pct_busquedas_test").to_frame())
    level_cov["pct_busquedas_train_oraculo"] = train["oracle_base_level"].value_counts(normalize=True)
    level_cov = level_cov.reindex([n for n, _ in config.CASCADE_LEVELS] + [config.NO_SUPPORT_LEVEL]).fillna(0)
    level_cov.index.name = "nivel"

    hyb = "pred_E_hibrido_cascada"
    errors = {g: metrics_by_group(ev, "is_deal", hyb, g)
              for g in ["base_level", "tier", "mapeo", "price_bucket", "stay_duration", "month"]}
    if do_ml:
        errors_ml = {g: metrics_by_group(ev, "is_deal", "pred_F_ml_hist_gradient_boosting", g)
                     for g in ["tier", "price_bucket"]}
    else:
        errors_ml = {}
    # Errores típicos del híbrido: FP con descuento cercano al umbral / FN por mercado que cambió
    ev["error_tipo"] = np.select(
        [(ev[hyb] == 1) & (y == 0), (ev[hyb] == 0) & (y == 1)], ["FP", "FN"], default="ok")
    ev["shift_mediana"] = ev["oracle_base_median"] / ev["base_median"] - 1
    error_profile = (ev[ev[hyb].notna()].groupby("error_tipo")
                     .agg(n=("price_std", "size"), descuento_mediano=("discount", "median"),
                          z_log_mediano=("z_log", "median"),
                          cambio_mediana_mercado=("shift_mediana", "median"),
                          soporte_mediano=("base_n_records", "median")).reset_index())

    # 7. Sensibilidad -------------------------------------------------------
    sens = sensitivity(train_raw, test_raw, test["is_deal"]) if do_sensitivity else pd.DataFrame()

    # 8. Artefactos para la API ----------------------------------------------
    art = config.artifacts_dir(source)
    cascade.save(art / "baselines")
    params = {
        "data_source": source, "train_year": config.TRAIN_YEAR, "test_year": config.TEST_YEAR,
        "winsor_quantile": config.WINSOR_QUANTILE, "winsor_cap": winsor.cap_,
        "price_std_floor": config.PRICE_STD_FLOOR, "z_log_threshold": config.Z_LOG_THRESHOLD,
        "min_discount": config.MIN_DISCOUNT, "min_support": config.MIN_SUPPORT,
        "support_column": config.SUPPORT_COLUMN, "train_prevalence": prevalence,
        "n_train": int(len(train)), "n_test": int(len(test)),
    }
    (art / "params.json").write_text(json.dumps(params, indent=2), encoding="utf-8")

    # 9. Test set compartido (evaluado de punta a punta con el servicio) ------
    test["tier"] = ts.destination_tier(test, train)
    real_q = ts.build_real(test)
    syn_q, syn_int = ts.build_synthetic(test)
    detector = DealDetector(art)
    edge_q = ts.fill_edge_prices(ts.build_edge_cases(train), detector)
    test_set = pd.concat([real_q, syn_q, edge_q], ignore_index=True)
    test_set.insert(0, "query_id", [f"q{i:05d}" for i in range(len(test_set))])
    resp = detector.evaluate_frame(test_set)
    test_set_eval = test_set.join(resp.add_prefix("api_"))

    ts_metrics = []
    for ct in ["real", "sintetico"]:
        sub = test_set_eval[test_set_eval["case_type"] == ct]
        m = classification_metrics(sub["expected_is_deal"], sub["api_is_deal"].astype(float))
        m["bloque"] = ct
        ts_metrics.append(m)
    ts_metrics = pd.DataFrame(ts_metrics)
    edge_eval = test_set_eval[test_set_eval["case_type"] == "borde"][
        ["query_id", "descripcion", "expected_decision", "api_decision", "api_baseline_level"]].copy()
    edge_eval["ok"] = [a in e.split("|") for a, e in zip(edge_eval["api_decision"], edge_eval["expected_decision"])]

    # Sintéticos: tasa de marcado por factor, para todos los algoritmos
    syn_preds, _ = _baseline_predictions(syn_int, cascade)
    for name, mdl in models.items():
        syn_preds[name] = mdl.predict(syn_int)
    syn_rows = []
    for name, p in syn_preds.items():
        for f in ts.SYNTHETIC_FACTORS:
            mask = (syn_int["price_factor"] == f).values
            pp = p[mask]
            syn_rows.append({"algoritmo": name, "factor_precio": f,
                             "pct_marcado_deal": float(np.nanmean(pp)) if np.isfinite(pp).any() else np.nan,
                             "pct_verdad_deal": float(syn_int.loc[mask, "is_deal"].mean())})
    syn_by_factor = pd.DataFrame(syn_rows).pivot_table(index="algoritmo", columns="factor_precio",
                                                       values="pct_marcado_deal")
    syn_truth = pd.DataFrame(syn_rows).groupby("factor_precio")["pct_verdad_deal"].first()
    syn_by_factor.loc["VERDAD (regla sobre mercado 2025)"] = syn_truth
    syn_metrics = metrics_table(syn_int["is_deal"], syn_preds)

    R.update(dict(
        train=train, test=test, ev=ev, metrics=metrics, metrics_weighted=metrics_w,
        metrics_random=metrics_random, level_coverage=level_cov, errors=errors, errors_ml=errors_ml,
        error_profile=error_profile, sensitivity=sens, params=params, test_set=test_set,
        test_set_eval=test_set_eval, test_set_metrics=ts_metrics, edge_eval=edge_eval,
        synthetic_by_factor=syn_by_factor, synthetic_truth=syn_truth, synthetic_metrics=syn_metrics,
        models=models,
    ))

    # 10. Escritura -----------------------------------------------------------
    if write:
        funnel.to_csv(out / "embudo_curacion.csv", index=False)
        metrics.to_csv(out / "metricas_test_temporal.csv", index=False)
        metrics_w.to_csv(out / "metricas_test_temporal_ponderadas.csv", index=False)
        metrics_random.to_csv(out / "metricas_split_aleatorio_2024.csv", index=False)
        level_cov.to_csv(out / "cobertura_por_nivel_cascada.csv")
        for g, t in errors.items():
            t.to_csv(out / f"errores_hibrido_por_{g}.csv", index=False)
        for g, t in errors_ml.items():
            t.to_csv(out / f"errores_ml_por_{g}.csv", index=False)
        error_profile.to_csv(out / "perfil_errores_hibrido.csv", index=False)
        if len(sens):
            sens.to_csv(out / "sensibilidad.csv", index=False)
        syn_by_factor.to_csv(out / "sinteticos_tasa_marcado_por_factor.csv")
        syn_metrics.to_csv(out / "metricas_sinteticos.csv", index=False)
        ts_metrics.to_csv(out / "metricas_test_set_compartido_api.csv", index=False)
        edge_eval.to_csv(out / "casos_borde_api.csv", index=False)
        config.TEST_SET_DIR.mkdir(parents=True, exist_ok=True)
        test_set.to_csv(config.TEST_SET_DIR / f"test_set_{source}.csv", index=False)
        test_set_eval.to_csv(out / "test_set_respuestas_api.csv", index=False)
        summary = {
            "source": source, "n_train": len(train), "n_test": len(test), "n_test_evaluable": len(ev),
            "test_evaluable_pct": len(ev) / len(test), "train_prevalence": prevalence,
            "test_prevalence": float(y.mean()), "winsor_cap": winsor.cap_,
            "ml_thresholds": {k: m.threshold_ for k, m in models.items()},
            "ml_val_f1": {k: m.val_f1_ for k, m in models.items()},
            "test_set_rows": test_set["case_type"].value_counts().to_dict(),
            "edge_cases_ok": int(edge_eval["ok"].sum()), "edge_cases_total": len(edge_eval),
            "runtime_s": round(time.time() - t0, 1),
        }
        (out / "resumen.json").write_text(json.dumps(summary, indent=2, default=float), encoding="utf-8")
        R["summary"] = summary
        if len(sens) and models:
            from .figures import save_all
            save_all(source)
    log.info("Pipeline completo en %.0fs", time.time() - t0)
    return R
