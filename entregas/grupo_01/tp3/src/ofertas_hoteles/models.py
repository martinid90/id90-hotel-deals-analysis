"""Los algoritmos que se comparan. Todos se ajustan SOLO con train (2024).

Interfaz común:
    m.fit(train)
    m.predict(df, param=None) -> DataFrame con
        decision   : 'oferta' | 'normal' | 'sospechoso' | 'sin_soporte'
        is_deal    : bool (decision == 'oferta')
        has_support: bool (el sistema pudo decidir)
        level      : nivel de contexto usado
        ref_price  : precio típico de referencia (si aplica)
`param` es el umbral principal de cada modelo; `grid` son los valores que se prueban en validación.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from . import config
from .references import assign_bucket, fit_bucket_cuts, fit_level_tables, resolve


def _frame(df, decision, level, ref_price, **extra) -> pd.DataFrame:
    out = pd.DataFrame({"decision": decision, "level": level, "ref_price": ref_price}, index=df.index)
    out["is_deal"] = out["decision"].eq("oferta")
    out["has_support"] = out["decision"].ne("sin_soporte")
    for k, v in extra.items():
        out[k] = v
    return out


class BaseModel:
    name = "base"
    param_name = "umbral"
    grid: list = []
    default = None

    def __init__(self, param=None):
        self.param = self.default if param is None else param

    def fit(self, train: pd.DataFrame):
        return self

    def predict(self, df: pd.DataFrame, param=None) -> pd.DataFrame:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# 1. Baseline aleatorio
# ---------------------------------------------------------------------------
class RandomBaseline(BaseModel):
    """Marca oferta al azar con probabilidad p. Es el piso: cualquier algoritmo útil tiene que superarlo."""
    name = "1_aleatorio"
    param_name = "p"
    grid = [0.05, 0.10, 0.20, 0.30, 0.44]
    default = 0.10

    def predict(self, df, param=None):
        p = self.param if param is None else param
        # semilla derivada del search_id → la misma búsqueda siempre recibe el mismo sorteo
        h = pd.util.hash_pandas_object(df["search_id"], index=False).values
        u = (h % 1_000_003) / 1_000_003
        dec = np.where(u < p, "oferta", "normal")
        return _frame(df, dec, "global", np.nan)


# ---------------------------------------------------------------------------
# 2. Baseline regla simple por mediana
# ---------------------------------------------------------------------------
class MedianRule(BaseModel):
    """Oferta si precio <= (1 - c) × mediana del contexto (destino × mes con fallback)."""
    name = "2_mediana_regla"
    param_name = "c"
    grid = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
    default = 0.25
    levels = config.LEVELS_A

    def fit(self, train):
        self.tables = fit_level_tables(train, self.levels)
        return self

    def predict(self, df, param=None):
        c = self.param if param is None else param
        r = resolve(df, self.tables, self.levels)
        ref = np.exp(r["med_log"])
        sup = r["level"].ne("sin_soporte")
        dec = np.select([~sup, df["price"] <= (1 - c) * ref], ["sin_soporte", "oferta"], default="normal")
        return _frame(df, dec, r["level"], ref)


# ---------------------------------------------------------------------------
# 3. Algoritmo propuesto (Pupi): z robusto (mediana/MAD en log) + descuento mínimo
#    + filtro de errores de carga + fallback jerárquico. Contexto A = destino × mes.
# ---------------------------------------------------------------------------
class ProposedRobust(BaseModel):
    name = "3_propuesto_robusto_A"
    param_name = "z_cut"
    grid = [-1.0, -1.25, -1.5, -1.75, -2.0, -2.5]
    default = -1.5
    levels = config.LEVELS_A
    uses_bucket = False
    abs_floor = False  # v2: el filtro de errores es solo relativo al contexto (ver ProposedRobustV1)

    def fit(self, train):
        if self.uses_bucket:
            self.cuts = fit_bucket_cuts(train)
            train = train.assign(price_bucket=assign_bucket(train, self.cuts))
        self.tables = fit_level_tables(train, self.levels)
        self.piso_abs = float(train["price"].quantile(0.01))
        return self

    def _prepare(self, df):
        if self.uses_bucket:
            # el bucket se recalcula con el precio que se evalúa (como en producción)
            df = df.assign(price_bucket=assign_bucket(df, self.cuts))
        return df

    def predict(self, df, param=None):
        z_cut = self.param if param is None else param
        df = self._prepare(df)
        r = resolve(df, self.tables, self.levels)
        mad = np.maximum(r["mad_log"], config.MAD_MIN)
        z = (df["log_price"] - r["med_log"]) / (config.K_MAD * mad)
        ref = np.exp(r["med_log"])
        desc = 1 - df["price"] / ref
        sup = r["level"].ne("sin_soporte")
        # sospechoso = probable error de carga: precio < 20% del típico de SU contexto.
        # v1 agregaba un piso absoluto global (p1 de train): se descartó en validación porque
        # castiga a los mercados baratos (ver ProposedRobustV1 y el reporte).
        sosp = sup & (df["price"] < config.FACTOR_SOSP * ref)
        if self.abs_floor:
            sosp |= sup & ((df["price"] < self.piso_abs) | (ref < self.piso_abs))
        deal = sup & ~sosp & (z < z_cut) & (desc >= config.DESC_MIN)
        dec = np.select([~sup, sosp, deal], ["sin_soporte", "sospechoso", "oferta"], default="normal")
        return _frame(df, dec, r["level"], ref, z=z, descuento=desc)


class ProposedRobustV1(ProposedRobust):
    """Versión anterior (tp3_pupi v1): además del filtro relativo, marca 'sospechoso' todo precio por
    debajo del percentil 1 global de train. Se mantiene para documentar por qué se cambió."""
    name = "3c_propuesto_v1_piso_abs"
    abs_floor = True


class ProposedRobustB(ProposedRobust):
    """Misma regla sobre el Escenario B (destino × mes × price_bucket). Se incluye para medir
    el costo de que el bucket dependa del precio evaluado (limitación del Escenario B)."""
    name = "3b_propuesto_robusto_B"
    levels = config.LEVELS_B
    uses_bucket = True


# ---------------------------------------------------------------------------
# 4. MAD puro (z modificado de Iglewicz–Hoaglin), sin reglas de negocio
# ---------------------------------------------------------------------------
class PureMAD(BaseModel):
    """Oferta si M = 0,6745 × (log p − mediana) / MAD < corte (cola inferior).
    Es el detector de outliers robusto "de libro": sin descuento mínimo ni filtro de errores."""
    name = "4_mad_puro"
    param_name = "m_cut"
    grid = [-1.0, -1.5, -2.0, -2.5, -3.0, -3.5]
    default = -3.5
    levels = config.LEVELS_A

    def fit(self, train):
        self.tables = fit_level_tables(train, self.levels)
        return self

    def predict(self, df, param=None):
        cut = self.param if param is None else param
        r = resolve(df, self.tables, self.levels)
        m = 0.6745 * (df["log_price"] - r["med_log"]) / np.maximum(r["mad_log"], 1e-3)
        sup = r["level"].ne("sin_soporte")
        dec = np.select([~sup, m < cut], ["sin_soporte", "oferta"], default="normal")
        return _frame(df, dec, r["level"], np.exp(r["med_log"]), m=m)


# ---------------------------------------------------------------------------
# 5. Isolation Forest (no supervisado, multivariado)
# ---------------------------------------------------------------------------
class IsolationForestModel(BaseModel):
    """Isolation Forest sobre: desvío robusto del precio respecto de su contexto, nivel de precio del
    contexto, noches, personas por habitación, habitaciones y mes (seno/coseno).
    Oferta = la búsqueda es de las más 'aislables' (top q% de anomalía en train) Y está por debajo
    de la referencia (el bosque detecta raros en ambas colas; solo nos interesan los baratos)."""
    name = "5_isolation_forest"
    param_name = "q"
    grid = [0.02, 0.05, 0.10, 0.15, 0.20, 0.30]
    default = 0.10
    levels = config.LEVELS_A
    n_fit = 200_000

    def _features(self, df, r):
        mad = np.maximum(r["mad_log"], config.MAD_MIN)
        return np.column_stack([
            (df["log_price"] - r["med_log"]) / (config.K_MAD * mad),
            r["med_log"],
            np.log(df["nights"]),
            df["pax_per_room"],
            df["number_of_rooms"],
            np.sin(2 * np.pi * df["month"] / 12),
            np.cos(2 * np.pi * df["month"] / 12),
        ])

    def fit(self, train):
        self.tables = fit_level_tables(train, self.levels)
        tr = train.sample(min(self.n_fit, len(train)), random_state=config.SEED)
        r = resolve(tr, self.tables, self.levels)
        ok = r["level"].ne("sin_soporte").values
        X = self._features(tr[ok], r[ok])
        self.forest = IsolationForest(n_estimators=200, random_state=config.SEED, n_jobs=-1).fit(X)
        self.train_scores = -self.forest.score_samples(X)  # más alto = más anómalo
        return self

    def predict(self, df, param=None):
        q = self.param if param is None else param
        thr = np.quantile(self.train_scores, 1 - q)
        r = resolve(df, self.tables, self.levels)
        sup = r["level"].ne("sin_soporte").values
        score = np.full(len(df), np.nan)
        if sup.any():
            score[sup] = -self.forest.score_samples(self._features(df[sup], r[sup]))
        below = (df["log_price"] < r["med_log"]).values
        dec = np.select([~sup, (score >= thr) & below], ["sin_soporte", "oferta"], default="normal")
        return _frame(df, dec, r["level"], np.exp(r["med_log"]), if_score=score)


# ---------------------------------------------------------------------------
# 6. z-score clásico del grupo (media/desvío en log, Escenario semana × bucket)
# ---------------------------------------------------------------------------
class GroupZScore(BaseModel):
    """Versión del grupo (scoring_tp3.py) adaptada a búsqueda: z = (log p − media)/desvío < z_cut
    y descuento vs mediana >= 20%, con fallback destino×mes×semana×bucket → destino×mes×bucket → destino."""
    name = "6_zscore_grupo"
    param_name = "z_cut"
    grid = [-0.5, -1.0, -1.5, -2.0]
    default = -1.0
    levels = config.LEVELS_GRUPO

    def fit(self, train):
        self.cuts = fit_bucket_cuts(train)
        train = train.assign(price_bucket=assign_bucket(train, self.cuts))
        self.tables = fit_level_tables(train, self.levels)
        return self

    def predict(self, df, param=None):
        z_cut = self.param if param is None else param
        df = df.assign(price_bucket=assign_bucket(df, self.cuts))
        r = resolve(df, self.tables, self.levels, require_std=True)
        z = (df["log_price"] - r["mean_log"]) / r["std_log"]
        ref = np.exp(r["med_log"])
        rel = 1 - df["price"] / ref
        sup = r["level"].ne("sin_soporte")
        dec = np.select([~sup, (z < z_cut) & (rel >= 0.20)], ["sin_soporte", "oferta"], default="normal")
        return _frame(df, dec, r["level"], ref, z=z)


ALL_MODELS = [RandomBaseline, MedianRule, ProposedRobust, ProposedRobustV1, ProposedRobustB, PureMAD, IsolationForestModel, GroupZScore]
