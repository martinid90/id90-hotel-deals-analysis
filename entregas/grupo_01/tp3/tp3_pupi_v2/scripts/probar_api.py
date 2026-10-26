"""Manda las queries de ejemplo a la API (local o en Docker) e imprime las respuestas.

    python scripts/probar_api.py                       # usa http://localhost:8000
    python scripts/probar_api.py http://otra-url:8000
"""
import json
import sys
import urllib.request
from pathlib import Path

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
batch = json.loads((Path(__file__).resolve().parents[1] / "examples" / "queries_batch.json").read_text(encoding="utf-8"))

req = urllib.request.Request(f"{URL}/predict/batch", data=json.dumps(batch).encode(), headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req) as r:
    for q, res in zip(batch, json.loads(r.read())):
        print(f"{q['city']:<18} precio={q['price']:>7} → oferta: {res['oferta']:<3} ({res['decision']}) ref={res['precio_referencia']} "
              f"nivel={res['nivel_contexto']:<12} confianza={res['confianza']}")
