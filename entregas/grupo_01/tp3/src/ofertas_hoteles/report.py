"""Figuras del reporte (PNG en outputs/figuras)."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from . import config

INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
COLORS = {  # color fijo por modelo (paleta categórica validada, orden fijo)
    "3_propuesto_robusto_A": "#2a78d6",
    "4_mad_puro": "#eb6834",
    "5_isolation_forest": "#1baf7a",
    "2_mediana_regla": "#eda100",
    "6_zscore_grupo": "#e87ba4",
    "3b_propuesto_robusto_B": "#6250d6",
    "3c_propuesto_v1_piso_abs": "#008300",
    "1_aleatorio": "#9a9893",
}
LABELS = {
    "1_aleatorio": "Aleatorio", "2_mediana_regla": "Regla mediana", "3_propuesto_robusto_A": "Propuesto (A)",
    "3b_propuesto_robusto_B": "Propuesto con bucket (B)", "3c_propuesto_v1_piso_abs": "Propuesto v1 (piso abs.)",
    "4_mad_puro": "MAD puro", "5_isolation_forest": "Isolation Forest", "6_zscore_grupo": "z-score grupo",
}


def _style(ax):
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    for s in ["left", "bottom"]:
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(color=GRID, lw=0.8)
    ax.set_axisbelow(True)


def make_figures():
    out = config.OUTPUTS_DIR / "figuras"
    out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 10, "text.color": INK, "axes.labelcolor": INK2})

    # 1) Curva de detección por variación de precio
    c = pd.read_csv(config.OUTPUTS_DIR / "curva_por_variacion.csv")
    main = ["3_propuesto_robusto_A", "2_mediana_regla", "5_isolation_forest", "1_aleatorio"]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.axvspan(-62, -28, color="#2a78d6", alpha=0.06)
    ax.axvspan(-22, -8, color="#9a9893", alpha=0.10)
    ax.text(-45, 1.03, "oferta clara", ha="center", color=INK2, fontsize=9)
    ax.text(-15, 1.03, "zona gris", ha="center", color=INK2, fontsize=9)
    ax.text(20, 1.03, "no oferta", ha="center", color=INK2, fontsize=9)
    ax.text(-90, 1.03, "error\nde carga", ha="center", color=INK2, fontsize=9)
    for m in main:
        s = c[c["modelo"] == m].sort_values("variacion_pct")
        lw = 2.8 if m.startswith("3_") else 1.8
        ls = "--" if m == "1_aleatorio" else "-"
        ax.plot(s["variacion_pct"], s["oferta"], marker="o", ms=5, lw=lw, ls=ls, color=COLORS[m], label=LABELS[m])
    ax.set_xticks(sorted(c["variacion_pct"].unique()))
    ax.set_xlabel("Variación aplicada al precio del ancla (%)")
    ax.set_ylabel("Proporción marcada como oferta")
    ax.set_ylim(-0.02, 1.1)
    ax.set_title("¿Qué marca cada algoritmo según cuánto se modificó el precio? (test)", loc="left", fontsize=11)
    _style(ax)
    ax.legend(frameon=False, fontsize=9, loc="center right")
    fig.tight_layout()
    fig.savefig(out / "curva_deteccion.png", dpi=150)
    plt.close(fig)

    # 2) Métricas principales con IC 95%
    m = pd.read_csv(config.OUTPUTS_DIR / "metricas_test.csv")
    m = m[m["modelo"].isin(config.MODELOS_PRINCIPALES)].sort_values("f1")
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.2), sharey=True)
    for ax, (col, title) in zip(axes, [("f1", "F1"), ("precision", "Precisión"), ("recall", "Recall"), ("fpr", "Tasa de falsos positivos")]):
        lo_hi = m[f"{col}_ic95"].str.strip("[]").str.split(",", expand=True).astype(float)
        err = [(m[col] - lo_hi[0]).clip(lower=0), (lo_hi[1] - m[col]).clip(lower=0)]
        colors = [COLORS[x] for x in m["modelo"]]
        ax.barh([LABELS[x] for x in m["modelo"]], m[col], color=colors, height=0.6, xerr=err, ecolor=INK2, capsize=2)
        for y, v in enumerate(m[col]):
            hi = lo_hi[1].iloc[y]
            ax.text(max(v, hi) + (0.003 if col == "fpr" else 0.02), y, f"{v:.3f}" if col == "fpr" else f"{v:.2f}",
                    va="center", fontsize=8, color=INK)
        ax.set_title(title, loc="left", fontsize=10)
        ax.set_xlim(0, 1.15 if col != "fpr" else max(0.12, m[col].max() * 1.4))
        _style(ax)
    fig.suptitle("Métricas en el set de test (barras = IC 95% por bootstrap de anclas)", x=0.01, ha="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(out / "metricas_test.png", dpi=150)
    plt.close(fig)

    # 3) Recall por nivel de precio del mercado (dónde falla cada uno)
    e = pd.read_csv(config.OUTPUTS_DIR / "errores_por_segmento.csv")
    order = ["muy_barato", "barato", "medio", "caro", "muy_caro"]
    d = e[e["dimension"] == "nivel_precio_mercado"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for mod in ["3_propuesto_robusto_A", "2_mediana_regla", "5_isolation_forest"]:
        s = d[d["modelo"] == mod].set_index("segmento").reindex(order)
        ax.plot(order, s["recall"], marker="o", lw=2.2 if mod.startswith("3_") else 1.6, color=COLORS[mod], label=LABELS[mod],
                ls="-")
    ax.set_ylabel("Recall sobre ofertas claras")
    ax.set_xlabel("Nivel de precio del mercado (quintiles de la mediana 2025)")
    ax.set_ylim(0, 1)
    ax.set_title("Recall según qué tan caro es el mercado (test)", loc="left", fontsize=11)
    _style(ax)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(out / "recall_por_nivel_precio.png", dpi=150)
    plt.close(fig)


def make_variants_figure():
    """Anexo: el modelo elegido contra las variantes que se probaron."""
    out = config.OUTPUTS_DIR / "figuras"
    c = pd.read_csv(config.OUTPUTS_DIR / "curva_por_variacion.csv")
    mods = ["4_mad_puro", "3b_propuesto_robusto_B", "3c_propuesto_v1_piso_abs",
            "6_zscore_grupo", "3_propuesto_robusto_A"]  # el elegido último, para que quede arriba
    fig, ax = plt.subplots(figsize=(9, 5))
    for m in mods:
        s = c[c["modelo"] == m].sort_values("variacion_pct")
        ax.plot(s["variacion_pct"], s["oferta"], marker="o", ms=4, lw=2.8 if m.startswith("3_") else 1.6,
                ls="-", color=COLORS[m], label=LABELS[m])
    ax.set_xticks(sorted(c["variacion_pct"].unique()))
    ax.set_xlabel("Variación aplicada al precio del ancla (%)")
    ax.set_ylabel("Proporción marcada como oferta")
    ax.set_ylim(-0.02, 1.05)
    ax.set_title("Anexo: modelo elegido vs. otras variantes probadas (test)", loc="left", fontsize=11)
    _style(ax)
    ax.legend(frameon=False, fontsize=9, loc="center right")
    fig.tight_layout()
    fig.savefig(out / "anexo_variantes.png", dpi=150)
    plt.close(fig)
