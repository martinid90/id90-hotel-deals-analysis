"""Clasificadores supervisados con features EXÓGENAS.

Anti-leakage: el modelo no recibe price_bucket, ni mediana/z/percentil del
contexto, ni ninguna variable derivada de la etiqueta. Solo ve el contexto de
la búsqueda y su precio, y tiene que aprender por sí mismo qué es "barato"
en cada contexto. Todos los encoders se ajustan solo con train.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import f1_score

from . import config

NUM_FEATURES = ["month", "week_in_month", "day_of_week", "nights", "number_of_adults",
                "number_of_kids", "number_of_rooms", "avg_hotel_count", "log_price"]
CAT_FEATURES = ["destination_final", "country_code"]
FEATURES = CAT_FEATURES + NUM_FEATURES


class FeatureEncoder:
    """Top-N categorías por frecuencia en train; el resto (y lo no visto) -> 'otro'."""

    def __init__(self, top=config.ML_TOP_CATEGORIES):
        self.top = top
        self.maps_ = {}

    def fit(self, df):
        for c in CAT_FEATURES:
            vc = df[c].value_counts()
            self.maps_[c] = {k: i for i, k in enumerate(vc.index[: self.top])}
        return self

    def transform(self, df):
        X = pd.DataFrame(index=df.index)
        for c in CAT_FEATURES:
            X[c] = df[c].map(self.maps_[c]).fillna(self.top).astype(int)
        for c in NUM_FEATURES:
            X[c] = df[c].astype(float)
        return X[FEATURES]


def _best_threshold(y, proba):
    grid = np.linspace(0.05, 0.95, 91)
    f1s = [f1_score(y, proba >= t, zero_division=0) for t in grid]
    return float(grid[int(np.argmax(f1s))])


class DealClassifier:
    """Entrena sobre el 80% de train y calibra el umbral de probabilidad
    (máximo F1) sobre el 20% restante de train. Test nunca se toca."""

    def __init__(self, kind="hgb", seed=config.SEED):
        self.kind = kind
        self.seed = seed
        self.encoder = FeatureEncoder()
        self.threshold_ = 0.5

    def _model(self):
        if self.kind == "hgb":
            return HistGradientBoostingClassifier(
                max_iter=300, learning_rate=0.1, max_leaf_nodes=63,
                categorical_features=[0, 1], random_state=self.seed)
        return RandomForestClassifier(n_estimators=200, min_samples_leaf=20, n_jobs=-1,
                                      random_state=self.seed)

    def fit(self, df, y):
        rng = np.random.default_rng(self.seed)
        df = df.reset_index(drop=True)
        y = np.asarray(y).astype(int)
        val = rng.random(len(df)) < 0.2
        fit_idx = np.flatnonzero(~val)
        if self.kind == "rf" and len(fit_idx) > config.ML_RF_MAX_TRAIN_ROWS:
            fit_idx = rng.choice(fit_idx, config.ML_RF_MAX_TRAIN_ROWS, replace=False)
        self.encoder.fit(df.iloc[fit_idx])
        self.model_ = self._model().fit(self.encoder.transform(df.iloc[fit_idx]), y[fit_idx])
        proba_val = self.predict_proba(df[val])
        self.threshold_ = _best_threshold(y[val], proba_val)
        self.val_f1_ = f1_score(y[val], proba_val >= self.threshold_, zero_division=0)
        return self

    def predict_proba(self, df):
        return self.model_.predict_proba(self.encoder.transform(df))[:, 1]

    def predict(self, df):
        return pd.Series((self.predict_proba(df) >= self.threshold_).astype(float), index=df.index)
