"""Métricas de evaluación.

Las métricas de clasificación se calculan sobre los casos donde el detector
decide; la cobertura mide qué fracción de los casos evaluables decide.
"""

import numpy as np
import pandas as pd


def classification_metrics(y_true, y_pred, weights=None):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    w = np.ones(len(y_true)) if weights is None else np.asarray(weights, dtype=float)
    # Población evaluable: casos con etiqueta de referencia definida
    labeled = ~np.isnan(y_true)
    y_true, y_pred, w = y_true[labeled], y_pred[labeled], w[labeled]
    decided = ~np.isnan(y_pred)
    yt, yp, ww = y_true[decided].astype(int), y_pred[decided].astype(int), w[decided]
    tp = ww[(yt == 1) & (yp == 1)].sum()
    fp = ww[(yt == 0) & (yp == 1)].sum()
    fn = ww[(yt == 1) & (yp == 0)].sum()
    tn = ww[(yt == 0) & (yp == 0)].sum()
    total = tp + fp + fn + tn
    precision = tp / (tp + fp) if tp + fp else np.nan
    recall = tp / (tp + fn) if tp + fn else np.nan
    pr_ok = np.isfinite(precision) and np.isfinite(recall) and precision + recall > 0
    f1 = 2 * precision * recall / (precision + recall) if pr_ok else 0.0
    return {
        "n_evaluables": int(len(y_true)),
        "n_decididos": int(decided.sum()),
        "cobertura": ww.sum() / w.sum() if w.sum() else np.nan,
        "accuracy": (tp + tn) / total if total else np.nan,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "fpr": fp / (fp + tn) if fp + tn else np.nan,
        "tasa_marcados": (tp + fp) / total if total else np.nan,
        "prevalencia": (tp + fn) / total if total else np.nan,
    }


def metrics_table(y_true, predictions, weights=None):
    rows = []
    for name, pred in predictions.items():
        m = classification_metrics(y_true, pred, weights)
        m["algoritmo"] = name
        rows.append(m)
    cols = ["algoritmo", "accuracy", "precision", "recall", "f1", "fpr", "cobertura",
            "tasa_marcados", "prevalencia", "n_evaluables", "n_decididos"]
    return pd.DataFrame(rows)[cols]


def metrics_by_group(df, label_col, pred_col, group_col):
    rows = []
    for g, sub in df.groupby(group_col, observed=True, dropna=False):
        m = classification_metrics(sub[label_col], sub[pred_col])
        m[group_col] = g
        rows.append(m)
    cols = [group_col, "n_evaluables", "cobertura", "precision", "recall", "f1", "fpr",
            "tasa_marcados", "prevalencia"]
    return pd.DataFrame(rows)[cols]
