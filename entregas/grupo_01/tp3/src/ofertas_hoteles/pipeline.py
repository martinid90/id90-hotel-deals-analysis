"""Corrida de punta a punta:

    python -m ofertas_hoteles.pipeline            # todo
    python -m ofertas_hoteles.pipeline --desde 2  # reusa las muestras ya generadas

Pasos
  1. Muestras 2024/2025 limpias con features         → data/interim/*.parquet
  2. Set de validación y set de test                  → data/val_set.csv.gz, data/test_set.csv.gz
  3. Ajuste de modelos (train) + umbral (val)          → outputs/grilla_validacion.csv, outputs/umbrales.json
  4. Evaluación final en test + análisis de errores    → outputs/*.csv, outputs/figuras/*.png
  5. Exportar el modelo final para la API              → models/
     + homogeneidad 2024 vs 2025 por mes                → outputs/estadistica/
  6. Diagnósticos sobre el dataset completo             → outputs/diagnosticos/
     (cobertura del mapeo y representatividad de la muestra)
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone

import pandas as pd

from . import config
from .data import build_samples
from .evaluate import bootstrap_ci, detection_curve, error_slices, metrics, metrics_weighted, tune
from .models import ALL_MODELS, ProposedRobust
from .testset import build_sets, load_set

log = logging.getLogger("pipeline")


def paso1():
    resumen = build_samples()
    config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(resumen).T.rename_axis("anio").to_csv(config.OUTPUTS_DIR / "resumen_datos.csv")


def _train():
    return pd.read_parquet(config.INTERIM_DIR / "muestra_2024.parquet")


def paso2():
    train = _train()
    df25 = pd.read_parquet(config.INTERIM_DIR / "muestra_2025.parquet")
    sets = build_sets(train, df25)
    for name in ["val", "test"]:
        sets[name].to_csv(config.DATA_DIR / f"{name}_set.csv.gz", index=False, compression=config.GZ)
        log.info("%s_set: %s casos", name, f"{len(sets[name]):,}")
    sets["_pools"].to_csv(config.OUTPUTS_DIR / "pools_2025.csv", index=False)

    # chequeo de fuga: ningún search_id ni grupo destino×fecha compartido entre pools
    v, t = sets["val"], sets["test"]
    g = lambda s: set(s["destination_final"].astype(str) + "|" + s["date_start"].astype(str))
    assert not set(v["search_id"]) & set(t["search_id"]), "search_id repetido entre val y test"
    assert not g(v) & g(t), "grupo destino×fecha repetido entre val y test"
    assert pd.to_datetime(t["date_start"]).dt.year.eq(2025).all() and train["date_start"].dt.year.eq(2024).all()

    # descripción del test set
    desc = []
    for name, s in [("val", v), ("test", t)]:
        anclas = s[s["tipo"] != "real"].drop_duplicates("anchor_id")
        for dim in ["tipo", "tier_destino", "nivel_precio_mercado", "trimestre", "is_mapped", "nivel_verdad"]:
            vc = s["tipo"].value_counts() if dim == "tipo" else anclas[dim].value_counts()
            for k, n in vc.items():
                desc.append({"set": name, "dimension": dim, "valor": str(k), "n": int(n)})
    pd.DataFrame(desc).to_csv(config.OUTPUTS_DIR / "descripcion_sets.csv", index=False)


def paso3_4():
    train = _train()
    val = load_set(config.DATA_DIR / "val_set.csv.gz")
    test = load_set(config.DATA_DIR / "test_set.csv.gz")

    grids, filas, filas_pond, curvas, slices, umbrales = [], [], [], [], [], {}
    for cls in ALL_MODELS:
        m = cls().fit(train)
        best, g = tune(m, val)
        grids.append(g)
        umbrales[m.name] = {"param": m.param_name, "valor": float(best)}
        pred = m.predict(test, best)
        filas.append({"modelo": m.name, "param": m.param_name, "valor": best,
                      **metrics(test, pred), **bootstrap_ci(test, pred)})
        filas_pond.append({"modelo": m.name, **metrics_weighted(test, pred)})
        curvas.append(detection_curve(test, pred, m.name))
        slices.append(error_slices(test, pred, m.name))
        pred.assign(case_id=test["case_id"].values).to_csv(
            config.OUTPUTS_DIR / "predicciones" / f"pred_test_{m.name}.csv.gz", index=False, compression=config.GZ)
        log.info("%s (%s=%s): %s", m.name, m.param_name, best, {k: round(v, 3) for k, v in filas[-1].items() if isinstance(v, float)})

    pd.concat(grids).to_csv(config.OUTPUTS_DIR / "grilla_validacion.csv", index=False)
    pd.DataFrame(filas).to_csv(config.OUTPUTS_DIR / "metricas_test.csv", index=False)
    pd.DataFrame(filas_pond).to_csv(config.OUTPUTS_DIR / "metricas_test_ponderadas.csv", index=False)
    pd.concat(curvas).to_csv(config.OUTPUTS_DIR / "curva_por_variacion.csv", index=False)
    pd.concat(slices).to_csv(config.OUTPUTS_DIR / "errores_por_segmento.csv", index=False)
    (config.OUTPUTS_DIR / "umbrales.json").write_text(json.dumps(umbrales, indent=2))


def paso5(z_cut: float | None = None):
    """Exporta el modelo final (propuesto, contexto A) con el umbral elegido en validación."""
    train = _train()
    if z_cut is None:
        z_cut = json.loads((config.OUTPUTS_DIR / "umbrales.json").read_text())[ProposedRobust.name]["valor"]
    m = ProposedRobust(z_cut).fit(train)
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for name, t in m.tables.items():
        t[t["n"] >= config.MIN_SUPPORT].to_csv(config.MODELS_DIR / f"referencias_{name}.csv.gz", index=False,
                                               compression=config.GZ)
    meta = {
        "modelo": m.name, "version": "tp3-v2",
        "entrenado_con": "búsquedas con check-in 2024 (muestra %.0f%%, semilla %d)" % (100 * config.FRAC_TRAIN_2024, config.SEED),
        "fecha_export": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "unidad_precio": config.PRICE_UNIT,
        "niveles": [[n, k] for n, k in m.levels], "min_soporte": config.MIN_SUPPORT,
        "z_cut": z_cut, "desc_min": config.DESC_MIN, "factor_sospechoso": config.FACTOR_SOSP,
        "k_mad": config.K_MAD, "mad_min": config.MAD_MIN, "piso_abs": m.piso_abs,
    }
    (config.MODELS_DIR / "modelo_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    log.info("Modelo exportado en %s", config.MODELS_DIR)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s | %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", type=int, default=1, help="paso desde el que arrancar (1-6)")
    ap.add_argument("--hasta", type=int, default=6)
    a = ap.parse_args()
    (config.OUTPUTS_DIR / "predicciones").mkdir(parents=True, exist_ok=True)
    pasos = {1: paso1, 2: paso2, 3: paso3_4, 5: paso5}
    for i in [1, 2, 3, 5]:
        if a.desde <= i <= a.hasta:
            log.info("===== Paso %d =====", i)
            pasos[i]()
    if a.desde <= 5 <= a.hasta:
        from .report import make_figures, make_variants_figure
        make_figures()
        make_variants_figure()
        from .estadistica import run as run_estadistica
        run_estadistica()  # homogeneidad 2024 vs 2025 → outputs/estadistica/
    if a.desde <= 6 <= a.hasta:
        log.info("===== Paso 6 (diagnósticos, dataset completo por chunks) =====")
        from .diagnostics import run as run_diagnostics
        run_diagnostics()


if __name__ == "__main__":
    main()
