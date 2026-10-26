"""Tests de la API: casos normales, fallback y entradas inválidas (no debe romper)."""
from fastapi.testclient import TestClient

from ofertas_hoteles.api import app

client = TestClient(app)
BASE = {"city": "Orlando", "state": "Florida", "country": "United States of America", "country_code": "us",
        "date_start": "2025-07-10", "date_end": "2025-07-13", "adults": 2, "kids": 0, "rooms": 1}


def post(**kw):
    return client.post("/predict", json={**BASE, **kw})


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_destino_conocido_tiene_contexto_fino():
    r = post(price=150).json()
    assert r["destino"]["mapeado"] is True
    assert r["nivel_contexto"] == "destino_mes" and r["confianza"] == "alta"
    assert r["decision"] in {"normal", "oferta"}
    assert r["n_referencia"] >= 30 and r["demanda_referencia"] >= r["n_referencia"]   # soporte y demanda del contexto


def test_precio_muy_bajo_es_oferta_y_absurdo_es_sospechoso():
    ref = post(price=150).json()["precio_referencia"]
    r = post(price=ref * 0.5).json()
    assert r["decision"] == "oferta" and r["oferta"] == "SI"
    assert list(r)[0] == "oferta"                                              # el veredicto va primero
    assert post(price=ref * 0.05).json()["decision"] == "sospechoso"
    assert post(price=ref * 1.3).json()["oferta"] == "NO"
    assert post(price=ref * 0.05).json()["oferta"] == "NO"                    # sospechoso → NO


def test_ciudad_desconocida_cae_a_pais():
    r = post(city="Pueblo Inventado XYZ", state="Nowhere", price=100).json()
    assert r["destino"]["mapeado"] is False
    assert r["nivel_contexto"] in {"pais_mes", "pais"} and r["confianza"] == "baja"


def test_pais_desconocido_no_decide_pero_no_rompe():
    r = post(city="Atlantis", state=None, country="Atlantis", country_code="zz", price=100)
    assert r.status_code == 200
    assert r.json()["decision"] == "sin_soporte" and r.json()["oferta"] == "NO"


def test_nights_sin_date_end():
    q = {k: v for k, v in BASE.items() if k != "date_end"}
    r = client.post("/predict", json={**q, "nights": 3, "price": 120})
    assert r.status_code == 200
    assert r.json()["noches"] == 3                                            # las noches se devuelven (trazabilidad)
    # el precio no se divide por noches: misma respuesta con 1 o con 7 noches
    r1 = client.post("/predict", json={**q, "nights": 1, "price": 120}).json()
    r7 = client.post("/predict", json={**q, "nights": 7, "price": 120}).json()
    assert r1["precio_comparable"] == r7["precio_comparable"] == 120


def test_entradas_invalidas_dan_422():
    assert post(price=-5).status_code == 422
    assert post(date_end="2025-07-01", price=100).status_code == 422          # check-out antes del check-in
    assert post(nights=5, price=100).status_code == 422                       # no coincide con fechas
    assert client.post("/predict", json={"city": "Orlando"}).status_code == 422


def test_batch():
    r = client.post("/predict/batch", json=[{**BASE, "price": 80}, {**BASE, "price": 300}])
    assert r.status_code == 200 and len(r.json()) == 2
