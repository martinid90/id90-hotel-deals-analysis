"""Sensibilidad a la unidad de precio (sección 6 del notebook).

Repite la evaluación completa (muestras, sets, ajuste y test) con otras dos unidades de precio, en carpetas temporales
para no pisar la corrida principal:
  - formula_alternativa: avg_price_average / (noches × habitaciones × personas) en TODAS las filas (fórmula escrita del TP2)
  - codigo_repo: lo que realmente ejecutó auxiliary_functions.standardize_prices (por el bug threshold 1 / fallback 0
    solo divide cuando hay 2+ noches Y 2+ habitaciones: mezcla dos unidades)
y calcula la dispersión por unidad, las elasticidades de avg_price_average y cuántas filas divide el código del repo.

    python scripts/sensibilidad_unidad_precio.py   → outputs/sensibilidad_unidad_precio/*.csv
"""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

import numpy as np
import pandas as pd

from ofertas_hoteles import config
from ofertas_hoteles.data import comparable_price

CTX = ["destination_final", "month"]


def correr_unidad(out: Path, unidad: str, nombre: str):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        env = {**os.environ, "PYTHONPATH": str(PROJECT / "src"), "TP3_PRICE_UNIT": unidad,
               "TP3_RAW_DIR": str(config.RAW_DIR), "TP3_MAPPING_PATH": str(config.MAPPING_PATH),
               "TP3_DATA_DIR": str(tmp / "data"), "TP3_INTERIM_DIR": str(tmp / "data" / "interim"),
               "TP3_OUTPUTS_DIR": str(tmp / "outputs"), "TP3_MODELS_DIR": str(tmp / "models")}
        (tmp / "data").mkdir()
        (tmp / "outputs" / "predicciones").mkdir(parents=True)
        subprocess.run([sys.executable, "-m", "ofertas_hoteles.pipeline", "--hasta", "3"], env=env, check=True)
        pd.read_csv(tmp / "outputs" / "metricas_test.csv").to_csv(out / f"metricas_test_{nombre}.csv", index=False)
        pd.read_csv(tmp / "outputs" / "grilla_validacion.csv").to_csv(out / f"grilla_validacion_{nombre}.csv", index=False)


def dispersion_y_elasticidades(out: Path):
    t = pd.read_parquet(config.INTERIM_DIR / "muestra_2024.parquet")
    persons = (t["number_of_adults"] + t["number_of_kids"]).clip(lower=1)
    unidades = {
        "habitacion_noche": np.log(t["avg_price_average"]),
        "formula_alternativa": np.log(t["avg_price_average"] / (t["nights"] * t["number_of_rooms"] * persons)),
        "codigo_repo": np.log(comparable_price(t, "repo")),
    }
    filas = []
    for nombre, lp in unidades.items():
        d = t[CTX].assign(lp=lp)
        med = d.groupby(CTX)["lp"].transform("median")
        g = d.assign(dev=(d["lp"] - med).abs()).groupby(CTX)
        tab = pd.DataFrame({"n": g.size(), "mad": g["dev"].median()})
        tab = tab[tab["n"] >= config.MIN_SUPPORT]
        mad = tab["mad"].median()
        filas.append({"unidad": nombre, "contextos_destino_mes": len(tab), "mad_log_mediano": mad,
                      "descuento_minimo_detectable_z-1.5": 1 - np.exp(-1.5 * config.K_MAD * mad)})
    pd.DataFrame(filas).to_csv(out / "dispersion_por_unidad.csv", index=False)

    # Cuántas filas divide realmente el código del repo (bug threshold 1 / fallback 0)
    divide = (t["nights"] > 1) & (t["number_of_rooms"] > 1)
    pd.DataFrame([{
        "filas_muestra_2024": len(t),
        "pct_divididas_por_codigo_repo": 100 * divide.mean(),
        "pct_sin_dividir": 100 * (~divide).mean(),
        "pct_con_1_habitacion": 100 * (t["number_of_rooms"] == 1).mean(),
        "pct_con_1_noche": 100 * (t["nights"] == 1).mean(),
    }]).to_csv(out / "codigo_repo_filas_divididas.csv", index=False)

    # Elasticidades: pendiente de log(avg_price_average) contra log(variable), una variable por vez, DENTRO de cada
    # destino × mes (se resta la media del contexto a ambas). 0 = el precio no depende de esa cantidad; 1 = proporcional.
    X = pd.DataFrame({"noches": np.log(t["nights"]), "habitaciones": np.log(t["number_of_rooms"]),
                      "personas": np.log(persons)})
    y = np.log(t["avg_price_average"])
    keys = [t[c] for c in CTX]
    Xd = X - X.groupby(keys).transform("mean")
    yd = y - y.groupby(keys).transform("mean")
    beta = [(Xd[c] * yd).sum() / (Xd[c] ** 2).sum() for c in X.columns]
    pd.DataFrame({"variable": X.columns, "elasticidad_log_precio": beta}).to_csv(
        out / "elasticidades_avg_price_average.csv", index=False)


def main():
    out = config.OUTPUTS_DIR / "sensibilidad_unidad_precio"
    out.mkdir(parents=True, exist_ok=True)
    dispersion_y_elasticidades(out)
    correr_unidad(out, "formula_completa", "formula_alternativa")
    correr_unidad(out, "repo", "codigo_repo")
    for f in sorted(out.glob("*.csv")):
        print(f.name)


if __name__ == "__main__":
    main()
