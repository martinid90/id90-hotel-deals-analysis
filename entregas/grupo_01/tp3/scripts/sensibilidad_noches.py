"""Sensibilidad a la duración de la estadía (para no mezclar duraciones distintas).

Compara el propuesto (contexto destino × mes) contra la misma regla con contexto
destino × mes × grupo de noches (1 / 2-3 / 4-6 / 7+), con fallback a destino × mes → destino → país.
Usa la misma unidad de precio que todo el pipeline (avg_price_average, sin dividir), el mismo train,
validación y test. Requiere haber corrido antes los pasos 1 y 2 del pipeline.

    python scripts/sensibilidad_noches.py      → outputs/sensibilidad_noches/*.csv
"""
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

import numpy as np
import pandas as pd

from ofertas_hoteles import config
from ofertas_hoteles.evaluate import bootstrap_ci, metrics, tune
from ofertas_hoteles.models import ProposedRobust
from ofertas_hoteles.testset import load_set

GRUPOS = ["1", "2-3", "4-6", "7+"]


def grupo_noches(n: pd.Series) -> pd.Series:
    return pd.cut(n, [0, 1, 3, 6, 999], labels=GRUPOS).astype(str)


class ProposedNights(ProposedRobust):
    name = "3e_propuesto_noches"
    levels = [("destino_mes_noches", ["destination_final", "month", "g_noches"])] + config.LEVELS_A


def main():
    train = pd.read_parquet(config.INTERIM_DIR / "muestra_2024.parquet")
    val = load_set(config.DATA_DIR / "val_set.csv.gz")
    test = load_set(config.DATA_DIR / "test_set.csv.gz")
    for d in (train, val, test):
        d["g_noches"] = grupo_noches(d["nights"])
    out = config.OUTPUTS_DIR / "sensibilidad_noches"
    out.mkdir(parents=True, exist_ok=True)

    # 1) ¿Cambia el precio por noche con la duración, dentro del mismo destino × mes? (solo train)
    med = train.groupby(["destination_final", "month"])["log_price"].transform("median")
    dif = (np.exp((train["log_price"] - med).groupby(train["g_noches"]).median()) - 1) * 100
    share = train["g_noches"].value_counts(normalize=True) * 100
    pd.DataFrame({"dif_pct_vs_destino_mes": dif, "pct_busquedas": share}).reindex(GRUPOS) \
        .rename_axis("noches").to_csv(out / "precio_por_grupo_noches.csv")

    # 2) Mismo modelo, con y sin noches en el contexto (umbral elegido en validación, evaluado en test)
    filas, por_grupo = [], []
    etiquetados = test["label"].notna() & test["tipo"].ne("real")
    for cls in (ProposedRobust, ProposedNights):
        m = cls().fit(train)
        best, _ = tune(m, val)
        p = m.predict(test, best)
        filas.append({"modelo": m.name, "z_cut": best, **metrics(test, p), **bootstrap_ci(test, p),
                      "pct_anclas_nivel_noches": 100 * p.loc[test["tipo"].ne("real"), "level"].eq("destino_mes_noches").mean()})
        for g in GRUPOS:
            s = etiquetados & test["g_noches"].eq(g)
            mm = metrics(test[s], p[s])
            por_grupo.append({"modelo": m.name, "noches": g, "recall": mm["recall"], "fpr": mm["fpr"], "f1": mm["f1"]})
    pd.DataFrame(filas).to_csv(out / "metricas_test_contexto_noches.csv", index=False)
    pd.DataFrame(por_grupo).to_csv(out / "metricas_por_grupo_noches.csv", index=False)
    print(pd.DataFrame(filas)[["modelo", "precision", "recall", "f1", "fpr", "f1_ic95"]].round(3).to_string())


if __name__ == "__main__":
    main()
