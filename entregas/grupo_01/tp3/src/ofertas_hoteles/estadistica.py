"""Homogeneidad entre años: ¿2024 (con lo que aprende el modelo) se parece a 2025 (con lo que se prueba)?

    python -m ofertas_hoteles.estadistica     → outputs/estadistica/homogeneidad_por_mes.csv
"""
from __future__ import annotations

import pandas as pd

from . import config


def run(out_dir=None) -> pd.DataFrame:
    out = out_dir or config.OUTPUTS_DIR / "estadistica"
    out.mkdir(parents=True, exist_ok=True)
    train = pd.read_parquet(config.INTERIM_DIR / "muestra_2024.parquet", columns=["destination_final", "month", "price"])
    return homogeneidad_por_mes(train, out)


def homogeneidad_por_mes(train: pd.DataFrame, out) -> pd.DataFrame:
    """¿2024 (train) se parece a 2025 (test) mes a mes? Compara cantidad de búsquedas y precio mediano, global y
    a igual destino (mediana de la razón 2025/2024 entre destinos con 30+ búsquedas ese mes en ambos años).
    Agrega cómo le va al modelo elegido en cada mes del test (falsos positivos y detección)."""
    t25 = pd.read_parquet(config.INTERIM_DIR / "muestra_2025.parquet", columns=["destination_final", "month", "price"])
    filas = []
    for m in range(1, 13):
        a, b = train[train["month"] == m], t25[t25["month"] == m]
        ga = a.groupby("destination_final")["price"].agg(["size", "median"])
        gb = b.groupby("destination_final")["price"].agg(["size", "median"])
        j = ga.join(gb, lsuffix="_24", rsuffix="_25", how="inner")
        j = j[(j["size_24"] >= config.MIN_SUPPORT) & (j["size_25"] >= config.MIN_SUPPORT)]
        filas.append({"mes": m, "busquedas_2024": len(a), "busquedas_2025": len(b),
                      "mediana_2024": a["price"].median(), "mediana_2025": b["price"].median(),
                      "razon_mediana_global": b["price"].median() / a["price"].median(),
                      "razon_mediana_mismo_destino": (j["median_25"] / j["median_24"]).median(),
                      "destinos_comparados": len(j)})
    hom = pd.DataFrame(filas)
    pred_path = config.OUTPUTS_DIR / "predicciones" / "pred_test_3_propuesto_robusto_A.csv.gz"
    test_path = config.DATA_DIR / "test_set.csv.gz"
    if pred_path.exists() and test_path.exists():
        from .testset import load_set
        test = load_set(test_path)
        pred = pd.read_csv(pred_path)
        d = test[["case_id", "month", "label", "tipo"]].merge(pred[["case_id", "is_deal"]], on="case_id")
        lab = d[d["tipo"] != "real"].dropna(subset=["label"])
        hom = hom.merge(pd.DataFrame({
            "modelo_fpr_test": lab[lab["label"] == 0].groupby("month")["is_deal"].mean(),
            "modelo_recall_test": lab[lab["label"] == 1].groupby("month")["is_deal"].mean(),
            "modelo_alertas_reales": d[d["tipo"] == "real"].groupby("month")["is_deal"].mean(),
        }).rename_axis("mes").reset_index(), on="mes", how="left")
    hom.to_csv(out / "homogeneidad_por_mes.csv", index=False)
    return hom


if __name__ == "__main__":
    print(run().round(3).to_string())
