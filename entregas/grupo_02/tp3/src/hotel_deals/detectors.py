"""Detectores basados en el baseline histórico y etiqueta de referencia.

Convención: cada detector devuelve una Serie float con 1.0 (deal), 0.0 (no
deal) o NaN (no decide: sin soporte en ningún nivel de la cascada).
"""

import numpy as np
import pandas as pd

from . import config
from .baselines import CascadeBaseline


def scores(price_std, base):
    """z gaussiano, z logarítmico y descuento sobre la mediana del contexto."""
    p = np.asarray(price_std, dtype=float)
    std_floor = np.maximum(base["base_std"].fillna(0).values, 0.10 * base["base_mean"].values)
    z = (p - base["base_mean"].values) / std_floor
    std_log = np.maximum(base["base_std_log"].fillna(0).values, config.MIN_STD_LOG)
    z_log = (np.log(p) - base["base_mean_log"].values) / std_log
    discount = 1.0 - p / base["base_median"].values
    return pd.DataFrame({"z": z, "z_log": z_log, "discount": discount}, index=base.index)


def _decided(rule, base):
    out = rule.astype(float)
    out[base["base_level"].eq(config.NO_SUPPORT_LEVEL).values] = np.nan
    return out


def hybrid(price_std, base, z_thr=config.Z_LOG_THRESHOLD, min_disc=config.MIN_DISCOUNT):
    s = scores(price_std, base)
    return _decided(pd.Series((s["z_log"] < z_thr) & (s["discount"] >= min_disc), index=base.index), base)


def z_gaussian(price_std, base, z_thr=-1.0):
    s = scores(price_std, base)
    return _decided(pd.Series(s["z"] < z_thr, index=base.index), base)


def median_rule(price_std, base, min_disc=config.NAIVE_MEDIAN_DISCOUNT):
    s = scores(price_std, base)
    return _decided(pd.Series(s["discount"] >= min_disc, index=base.index), base)


def percentile10(price_std, base):
    p = pd.Series(np.asarray(price_std, dtype=float), index=base.index)
    return _decided(p < base["base_p10"], base)


def random_naive(n, prevalence, seed=config.SEED, index=None):
    rng = np.random.default_rng(seed)
    return pd.Series((rng.random(n) < prevalence).astype(float), index=index)


BASELINE_DETECTORS = {
    "B_naive_mediana_20": median_rule,
    "C_zscore_gaussiano": z_gaussian,
    "D_percentil_10": percentile10,
    "E_hibrido_cascada": hybrid,
}


def oracle_labels(df, **cascade_kwargs):
    """Etiqueta de referencia: regla híbrida sobre la distribución REALIZADA del
    propio período (el mercado que efectivamente ocurrió).

    Se usa para evaluar si la historia (train) anticipa qué precios resultan
    oferta en el mercado futuro (test). Devuelve label (NaN si el período no
    tiene soporte suficiente ni a nivel país) y los estadísticos usados.
    """
    cb = CascadeBaseline(**cascade_kwargs).fit(df)
    base = cb.lookup(df)
    label = hybrid(df["price_std"].values, base)
    out = base.add_prefix("oracle_")
    out["is_deal"] = label
    return out
