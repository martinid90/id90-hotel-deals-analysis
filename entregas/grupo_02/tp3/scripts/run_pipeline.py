"""Corre el pipeline completo del TP3 y escribe outputs/ y outputs/artifacts/.

Uso (desde la carpeta TP3_entrega):
    python scripts/run_pipeline.py                 # muestra 300k (rápido)
    python scripts/run_pipeline.py --source full   # CSV históricos completos
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hotel_deals import pipeline  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["sample", "full"], default="sample")
    ap.add_argument("--no-sensitivity", action="store_true")
    ap.add_argument("--no-ml", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    R = pipeline.run(args.source, do_sensitivity=not args.no_sensitivity, do_ml=not args.no_ml)
    import pandas as pd
    pd.set_option("display.width", 200)
    print(R["metrics"].round(3).to_string(index=False))
    print(R["summary"])
