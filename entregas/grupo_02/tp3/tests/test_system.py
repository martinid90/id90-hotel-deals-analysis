"""Tests de la cascada, las métricas y la API (requiere artefactos generados)."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from hotel_deals import config  # noqa: E402
from hotel_deals.baselines import CascadeBaseline  # noqa: E402
from hotel_deals.evaluation import classification_metrics  # noqa: E402

HAS_ARTIFACTS = (config.default_artifacts_dir() / "params.json").exists()


def _toy():
    rng = np.random.default_rng(0)
    n = 200
    df = pd.DataFrame({
        "destination_final": ["A"] * 150 + ["B"] * 50,
        "country_code": ["US"] * 200,
        "month": [1] * 100 + [2] * 100,
        "week_in_month": rng.integers(1, 5, n),
        "stay_duration": ["corta"] * n,
        "price_std": rng.lognormal(4, 0.4, n),
        "count_repeated": 1,
    })
    df["log_price"] = np.log(df["price_std"])
    return df


def test_cascade_falls_back_to_less_specific_level():
    df = _toy()
    cb = CascadeBaseline(min_support=60).fit(df)
    q = pd.DataFrame({"destination_final": ["A", "B", "C", None], "country_code": ["US", "US", "US", "ZZ"],
                      "month": [1, 2, 1, 1], "week_in_month": [1, 1, 1, 1], "stay_duration": ["corta"] * 4})
    levels = cb.lookup(q)["base_level"].tolist()
    assert levels[0] == "L2_dest_mes_estadia"        # A x mes 1 tiene 100 filas
    assert levels[1] == "L6_pais_mes_estadia"        # B solo tiene 50 -> sube a país
    assert levels[2] == "L6_pais_mes_estadia"        # destino desconocido -> país
    assert levels[3] == config.NO_SUPPORT_LEVEL      # país desconocido -> no decide


def test_metrics_ignore_undecided_and_unlabeled():
    m = classification_metrics([1, 0, 1, np.nan], [1, np.nan, 0, 1])
    assert m["n_evaluables"] == 3 and m["n_decididos"] == 2
    assert m["cobertura"] == pytest.approx(2 / 3)
    assert m["precision"] == 1.0 and m["recall"] == 0.5


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)


@pytest.mark.skipif(not HAS_ARTIFACTS, reason="correr scripts/run_pipeline.py primero")
class TestAPI:
    def test_health(self, client):
        assert client.get("/health").json()["status"] == "ok"

    def test_deal_and_expensive(self, client):
        base = {"city": "Miami Beach", "state": "Florida", "country": "United States", "country_code": "US",
                "date_start": "2025-07-10", "nights": 3, "adults": 2, "kids": 0, "rooms": 1}
        r = client.post("/evaluate", json={**base, "price_total": 100000.0 / 100}).json()
        assert r["decision"] in {"deal", "no_deal"}
        med = r["baseline_median"] * 6
        cheap = client.post("/evaluate", json={**base, "price_total": med * 0.2}).json()
        assert cheap["decision"] == "deal" and cheap["explanation"].startswith("Oferta")
        expensive = client.post("/evaluate", json={**base, "price_total": med * 3}).json()
        assert expensive["decision"] == "no_deal" and "encima" in expensive["explanation"]

    def test_never_fails_on_unknown_places(self, client):
        r = client.post("/evaluate", json={"city": "Atlantis", "country_code": "ZZ", "date_start": "2025-01-01",
                                           "nights": 2, "adults": 2, "price_total": 200}).json()
        assert r["decision"] == "insufficient_data"
        r = client.post("/evaluate", json={"city": None, "country_code": "US", "date_start": "2025-01-01",
                                           "nights": 2, "adults": 2, "price_total": 200}).json()
        assert r["baseline_level"] == "L6_pais_mes_estadia"

    def test_invalid_inputs(self, client):
        base = {"city": "Miami", "country_code": "US", "date_start": "2025-01-01", "adults": 2}
        assert client.post("/evaluate", json={**base, "nights": 0, "price_total": 200}).json()["decision"] == "invalid_input"
        assert client.post("/evaluate", json={**base, "nights": 2, "price_total": 1}).json()["decision"] == "invalid_price"

    def test_batch_matches_single(self, client):
        q = {"city": "Cancun", "country_code": "MX", "date_start": "2025-03-10", "nights": 4, "adults": 2,
             "price_total": 500}
        single = client.post("/evaluate", json=q).json()
        batch = client.post("/evaluate/batch", json=[q, q]).json()
        assert batch[0]["decision"] == single["decision"] and len(batch) == 2

    def test_shared_test_set_edge_cases(self):
        from hotel_deals.service import DealDetector
        src = config.default_artifacts_dir().name
        ts = pd.read_csv(config.TEST_SET_DIR / f"test_set_{src}.csv")
        edge = ts[ts["case_type"] == "borde"]
        res = DealDetector().evaluate_frame(edge)
        ok = [d in e.split("|") for d, e in zip(res["decision"], edge["expected_decision"])]
        assert all(ok)
