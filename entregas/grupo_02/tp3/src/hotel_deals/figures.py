"""Gráficos del informe, generados a partir de las tablas de outputs/<fuente>/.

No recalculan nada: leen los CSV que escribe pipeline.run, así el notebook
principal y los PNG de outputs/<fuente>/figuras/ muestran exactamente los
mismos números que el README y el reporte.

    python -m hotel_deals.figures full     # regenera los PNG
"""

import sys

import matplotlib

if "ipykernel" not in sys.modules:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from . import config  # noqa: E402

# El algoritmo elegido va en azul; las referencias, en colores fijos; el resto, en gris.
BLUE, ORANGE, AQUA, GRAY, INK, MUTED = "#2a78d6", "#eb6834", "#1baf7a", "#a3a29c", "#0b0b0b", "#52514e"
STYLE = {"figure.figsize": (10, 4.5), "axes.spines.top": False, "axes.spines.right": False,
         "axes.edgecolor": "#c3c2b7", "axes.grid": True, "grid.color": "#ecebe7", "axes.axisbelow": True,
         "font.size": 10, "text.color": INK, "axes.labelcolor": MUTED, "xtick.color": MUTED,
         "ytick.color": MUTED, "figure.facecolor": "white", "axes.facecolor": "white"}

NOMBRES = {
    "A_naive_aleatorio": "A Naive aleatorio",
    "B_naive_mediana_20": "B Mediana −20%",
    "C_zscore_gaussiano": "C Z-score gaussiano",
    "D_percentil_10": "D Percentil 10",
    "E_hibrido_cascada": "E Híbrido + cascada",
    "E2_hibrido_sin_semana_posthoc": "E2 Híbrido sin semana*",
    "F_ml_hist_gradient_boosting": "F HistGradientBoosting",
    "G_ml_random_forest": "G Random Forest",
}
ELEGIDO = "E_hibrido_cascada"


def load(source="full"):
    """Lee las tablas del pipeline en un dict."""
    d = config.output_dir(source)
    return {
        "metricas": pd.read_csv(d / "metricas_test_temporal.csv"),
        "aleatorio": pd.read_csv(d / "metricas_split_aleatorio_2024.csv"),
        "sinteticos": pd.read_csv(d / "sinteticos_tasa_marcado_por_factor.csv", index_col=0),
        "sensibilidad": pd.read_csv(d / "sensibilidad.csv"),
        "cobertura": pd.read_csv(d / "cobertura_por_nivel_cascada.csv", index_col=0),
        "bucket": pd.read_csv(d / "errores_hibrido_por_price_bucket.csv"),
    }


def _bar_labels(ax, values, fmt="{:.2f}"):
    for y, x in enumerate(values):
        ax.text(x, y, " " + fmt.format(x), va="center", fontsize=8, color=INK)


def comparacion_algoritmos(T):
    m = T["metricas"].set_index("algoritmo").drop(index="E2_hibrido_sin_semana_posthoc", errors="ignore")
    m = m.sort_values("f1")
    labels = [NOMBRES.get(a, a) for a in m.index]
    colors = [BLUE if a == ELEGIDO else GRAY for a in m.index]
    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), sharey=True)
        for ax, col, title, xmax in zip(axes, ["f1", "precision", "fpr"],
                                        ["F1 (criterio de selección)", "Precision", "Tasa de falsos positivos"],
                                        [1.05, 1.05, 0.36]):
            ax.barh(labels, m[col], color=colors, height=0.6)
            _bar_labels(ax, m[col])
            ax.set_xlim(0, xmax)
            ax.set_title(title, loc="left", color=INK)
            ax.grid(axis="y", visible=False)
        fig.suptitle("Test temporal 2025: el híbrido elegido (azul) contra las alternativas",
                     x=0.01, ha="left", color=INK, fontweight="bold")
        fig.tight_layout()
    return fig


def respuesta_descuentos(T):
    sf = T["sinteticos"]
    x = sf.columns.astype(float)
    series = [("VERDAD (regla sobre mercado 2025)", GRAY, "Verdad por definición", "--"),
              (ELEGIDO, BLUE, "E Híbrido (elegido)", "-"),
              ("F_ml_hist_gradient_boosting", AQUA, "F HistGB", "-"),
              ("B_naive_mediana_20", ORANGE, "B Mediana −20%", "-")]
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(10, 4.5))
        for key, c, lab, ls in series:
            if key in sf.index:
                ax.plot(x, 100 * sf.loc[key], color=c, lw=2, ls=ls, marker="o", ms=6, label=lab)
        ax.axvline(1.0, color="#c3c2b7", lw=1)
        ax.text(1.01, 95, "precio = mediana", color=MUTED, fontsize=8, va="top")
        ax.set_xticks(x)
        ax.set_xticklabels([f"{f:g}×\n({(f - 1):+.0%})" for f in x])
        ax.set_xlabel("Precio sintético = factor × mediana del mercado (entre paréntesis, descuento o recargo)")
        ax.set_ylabel("% de búsquedas marcadas como oferta")
        ax.set_ylim(-3, 103)
        ax.set_title("Casos controlados: cómo responde cada algoritmo a descuentos conocidos",
                     loc="left", color=INK, fontweight="bold")
        ax.legend(frameon=False, loc="upper right")
        fig.tight_layout()
    return fig


def ofertas_por_price_bucket(T):
    b = T["bucket"].set_index("price_bucket").reindex(["low", "medium", "high"])
    etiquetas = {"low": "low (≤ p25 del destino)", "medium": "medium", "high": "high (≥ p75 del destino)"}
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(9, 3.4))
        y = range(len(b))
        ax.barh([v - 0.17 for v in y], 100 * b["prevalencia"], height=0.32, color=GRAY, label="Ofertas reales (etiqueta)")
        ax.barh([v + 0.17 for v in y], 100 * b["tasa_marcados"], height=0.32, color=BLUE, label="Marcadas por E")
        for v, (p, t) in enumerate(zip(b["prevalencia"], b["tasa_marcados"])):
            ax.text(100 * p, v - 0.17, f" {p:.1%}", va="center", fontsize=8, color=INK)
            ax.text(100 * t, v + 0.17, f" {t:.1%}", va="center", fontsize=8, color=INK)
        ax.set_yticks(list(y))
        ax.set_yticklabels([etiquetas[i] for i in b.index])
        ax.invert_yaxis()
        ax.set_xlim(0, 60)
        ax.set_xlabel("% de búsquedas de test 2025")
        ax.set_title("price_bucket casi reproduce la etiqueta: por eso no se usa como feature",
                     loc="left", color=INK, fontweight="bold")
        ax.legend(frameon=False, loc="lower right")
        ax.grid(axis="y", visible=False)
        fig.tight_layout()
    return fig


def cobertura_cascada(T):
    c = T["cobertura"]["pct_busquedas_test"].iloc[::-1]
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(9, 3.4))
        colors = [GRAY if i == config.NO_SUPPORT_LEVEL else BLUE for i in c.index]
        labels = [f"{i[:2]} {config.LEVEL_LABELS.get(i, i)}" for i in c.index]
        ax.barh(labels, 100 * c.values, color=colors, height=0.6)
        _bar_labels(ax, 100 * c.values, "{:.1f}%")
        ax.set_xlim(0, 52)
        ax.set_xlabel("% de búsquedas de test 2025 resueltas en cada nivel")
        ax.set_title("Qué nivel de la cascada decide cada búsqueda", loc="left", color=INK, fontweight="bold")
        ax.grid(axis="y", visible=False)
        fig.tight_layout()
    return fig


def sensibilidad_contexto(T):
    s = T["sensibilidad"]
    s = s[s["bloque"] == "definición de contexto"].set_index("variante")
    orden = ["cascada completa (L1..L6)", "solo L1 (sin fallback)", "cascada sin semana (L2..L6)",
             "cascada sin nivel país (L1..L5)", "solo destino (L5)"]
    s = s.reindex(orden).iloc[::-1]
    colors = [BLUE if v.startswith("cascada completa") else GRAY for v in s.index]
    with plt.rc_context(STYLE):
        fig, axes = plt.subplots(1, 2, figsize=(12, 3.4), sharey=True)
        for ax, col, title in zip(axes, ["f1", "cobertura"], ["F1", "Cobertura (búsquedas donde decide)"]):
            ax.barh(s.index, s[col], color=colors, height=0.6)
            _bar_labels(ax, s[col], "{:.2f}" if col == "f1" else "{:.1%}")
            ax.set_xlim(0, 1.12)
            ax.set_title(title, loc="left", color=INK)
            ax.grid(axis="y", visible=False)
        fig.suptitle("Sensibilidad a la definición de mercado: hay que mirar F1 y cobertura juntos",
                     x=0.01, ha="left", color=INK, fontweight="bold")
        fig.tight_layout()
    return fig


def umbral_zlog(T):
    s = T["sensibilidad"]
    z = s[s["bloque"].str.startswith("umbral z_log")].copy()
    z["z"] = z["variante"].str.extract(r"(-?\d+\.?\d*)", expand=False).astype(float)
    with plt.rc_context(STYLE):
        fig, ax = plt.subplots(figsize=(8, 4))
        for col, c, lab in [("precision", BLUE, "Precision"), ("recall", ORANGE, "Recall"), ("fpr", GRAY, "FPR")]:
            ax.plot(z["z"], z[col], color=c, lw=2, marker="o", ms=6)
            ax.annotate(lab, (z["z"].iloc[-1], z[col].iloc[-1]), xytext=(8, 0), textcoords="offset points",
                        color=INK, fontsize=9, va="center")
        ax.axvline(-1.0, color="#c3c2b7", lw=1)
        ax.text(-1.0, 1.0, " umbral elegido", color=MUTED, fontsize=8, va="top")
        ax.invert_xaxis()
        ax.set_ylabel("Valor de la métrica")
        ax.set_xlabel("Umbral de z_log (más negativo = más exigente)")
        ax.set_title("Trade-off del umbral: más exigente sube precision y baja recall",
                     loc="left", color=INK, fontweight="bold")
        fig.tight_layout()
    return fig


FIGURAS = {
    "comparacion_algoritmos": comparacion_algoritmos,
    "respuesta_descuentos_sinteticos": respuesta_descuentos,
    "ofertas_por_price_bucket": ofertas_por_price_bucket,
    "cobertura_cascada": cobertura_cascada,
    "sensibilidad_contexto": sensibilidad_contexto,
    "umbral_zlog": umbral_zlog,
}


def save_all(source="full"):
    T = load(source)
    out = config.output_dir(source) / "figuras"
    out.mkdir(parents=True, exist_ok=True)
    for name, fn in FIGURAS.items():
        fig = fn(T)
        fig.savefig(out / f"{name}.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
    return out


if __name__ == "__main__":
    print(save_all(sys.argv[1] if len(sys.argv) > 1 else "full"))
