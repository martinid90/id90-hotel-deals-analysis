"""Scorer liviano para producción (lo usa la API).

Carga las tablas de referencia exportadas en models/ y aplica EXACTAMENTE la misma regla
que `models.ProposedRobust` (hay un test que lo verifica caso por caso sobre el test set).
No depende de scikit-learn ni de los datos crudos.
"""
from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

import pandas as pd

from . import config
from .mapping import DestinationMapper

CONFIANZA = {"destino_mes": "alta", "destino": "media", "pais_mes": "baja", "pais": "baja", "sin_soporte": "ninguna"}


class DealScorer:
    def __init__(self, models_dir: Path | str = config.MODELS_DIR, mapping_path: Path | str = config.MAPPING_PATH):
        models_dir = Path(models_dir)
        self.meta = json.loads((models_dir / "modelo_meta.json").read_text(encoding="utf-8"))
        self.levels = [(n, list(k)) for n, k in self.meta["niveles"]]
        self.tables = {}
        for name, keys in self.levels:
            t = pd.read_csv(models_dir / f"referencias_{name}.csv.gz", dtype={"destination_final": str, "cc": str},
                            keep_default_na=False, na_values=[""])
            self.tables[name] = {
                tuple(r[k] for k in keys): (int(r["n"]), float(r["med_log"]), float(r["mad_log"]),
                                            int(r["demanda"]) if "demanda" in r else None)
                for r in t.to_dict("records")
            }
        self.mapper = DestinationMapper(mapping_path)

    # -- precio comparable -------------------------------------------------------------
    def comparable_price(self, price: float, nights: int, rooms: int, persons: int) -> float:
        # Con la unidad por defecto (habitación-noche) el precio se usa tal cual: noches, habitaciones y personas
        # se reciben y se devuelven para trazar el contexto, pero NO se divide (no hay doble normalización).
        if self.meta["unidad_precio"] == "formula_completa":
            return price / (nights * rooms * max(persons, 1))
        return float(price)

    # -- regla -------------------------------------------------------------------------
    def score_context(self, destination_final: str, cc: str, month: int, price: float) -> dict:
        ctx = {"destination_final": destination_final, "cc": cc, "month": int(month)}
        level, ref = "sin_soporte", None
        for name, keys in self.levels:
            hit = self.tables[name].get(tuple(ctx[k] for k in keys))
            if hit and hit[0] >= self.meta["min_soporte"]:
                level, ref = name, hit
                break
        out = {"nivel_contexto": level, "confianza": CONFIANZA.get(level, "baja"), "n_referencia": None,
               "demanda_referencia": None, "precio_referencia": None, "descuento": None, "z_robusto": None}
        if ref is None:
            out.update(decision="sin_soporte", is_deal=False,
                       mensaje="No hay historial suficiente para este destino/país: el sistema no decide.")
            return out
        n, med_log, mad_log, demanda = ref
        ref_price = math.exp(med_log)
        z = (math.log(price) - med_log) / (self.meta["k_mad"] * max(mad_log, self.meta["mad_min"]))
        desc = 1 - price / ref_price
        if price < self.meta["factor_sospechoso"] * ref_price:
            dec, msg = "sospechoso", "Precio más de 80% por debajo del típico: probable error de carga, no se recomienda."
        elif z < self.meta["z_cut"] and desc >= self.meta["desc_min"]:
            dec, msg = "oferta", f"Precio {desc:.0%} por debajo del típico de su mercado."
        else:
            dec, msg = "normal", "Precio dentro de lo habitual para su mercado."
        out.update(decision=dec, is_deal=dec == "oferta", mensaje=msg, n_referencia=n, demanda_referencia=demanda,
                   precio_referencia=round(ref_price, 2), descuento=round(desc, 4), z_robusto=round(z, 3))
        return out

    def score_query(self, *, city: str, country_code: str, date_start: date, price: float, state: str | None = None,
                    country: str | None = None, nights: int = 1, adults: int = 2, kids: int = 0, rooms: int = 1) -> dict:
        geo = self.mapper.map_one(country_code, country, state, city)
        p = self.comparable_price(price, nights, rooms, adults + kids)
        res = self.score_context(geo["destination_final"], geo["cc"], date_start.month, p)
        res["precio_comparable"] = round(p, 2)
        res["noches"] = int(nights)
        res["destino"] = {"id": geo["destination_final"], "nombre": geo["destination_name"],
                          "mapeado": geo["is_mapped"], "match_level": geo["match_level"], "pais": geo["cc"]}
        return res
