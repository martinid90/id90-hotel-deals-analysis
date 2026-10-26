"""El scorer de producción (API) tiene que dar EXACTAMENTE lo mismo que el modelo evaluado."""
import pandas as pd
import pytest

from ofertas_hoteles import config
from ofertas_hoteles.scorer import DealScorer
from ofertas_hoteles.testset import load_set

PRED = config.OUTPUTS_DIR / "predicciones" / "pred_test_3_propuesto_robusto_A.csv.gz"


@pytest.mark.skipif(not PRED.exists(), reason="correr primero el pipeline")
def test_scorer_igual_al_modelo_evaluado():
    test = load_set(config.DATA_DIR / "test_set.csv.gz")
    pred = pd.read_csv(PRED)
    s = DealScorer()
    got = [s.score_context(d, c, m, p)["decision"]
           for d, c, m, p in zip(test["destination_final"], test["cc"], test["month"], test["price"])]
    assert (pd.Series(got) == pred["decision"]).mean() == 1.0


def test_sets_sin_fuga():
    val = load_set(config.DATA_DIR / "val_set.csv.gz")
    test = load_set(config.DATA_DIR / "test_set.csv.gz")
    assert test["case_id"].is_unique and val["case_id"].is_unique
    assert not set(val["search_id"]) & set(test["search_id"])
    key = lambda s: set(s["destination_final"] + "|" + s["date_start"].dt.strftime("%Y-%m-%d"))
    assert not key(val) & key(test)
    assert test["date_start"].dt.year.eq(2025).all()
    # etiquetas coherentes con el diseño
    assert test.loc[test["tipo"] == "oferta_clara", "factor"].le(0.70).all()
    assert test.loc[test["tipo"] == "no_oferta", "factor"].ge(1.0).all()
