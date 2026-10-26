"""Diagnósticos pedidos en la devolución del TP1 (sobre el dataset COMPLETO, leído por chunks):

1. Cobertura del mapeo: por filas, por demanda (count_repeated) y por geografías únicas,
   filas por `match_level` y principales geografías no mapeadas por demanda.
2. Representatividad de la muestra: ¿la muestra de cada año se parece al total en
   mes, país, destino y distribución de precios?
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from . import config
from .mapping import GEO_COLS, DestinationMapper

log = logging.getLogger(__name__)

PRICE_BINS = np.linspace(0, 12, 601)  # bins de log-precio para cuantiles aproximados del total
QS = [0.05, 0.25, 0.50, 0.75, 0.95]


def _valid(chunk: pd.DataFrame) -> pd.DataFrame:
    """Mismos filtros de calidad que data.clean (sin deduplicar)."""
    for c in ["number_of_adults", "number_of_rooms", "number_of_kids", "nights", "count_repeated", "avg_price_average"]:
        chunk[c] = pd.to_numeric(chunk[c], errors="coerce")
    chunk["number_of_kids"] = chunk["number_of_kids"].fillna(0)
    ds = pd.to_datetime(chunk["date_start"], errors="coerce")
    de = pd.to_datetime(chunk["date_end"], errors="coerce")
    ok = ((chunk["nights"] > 0) & (chunk["number_of_rooms"] > 0)
          & (chunk["number_of_adults"] + chunk["number_of_kids"] > 0)
          & (chunk["avg_price_average"] > 0) & ((de - ds).dt.days == chunk["nights"]) & (ds.dt.year.notna()))
    out = chunk[ok].copy()
    out["anio_archivo"] = ds[ok].dt.year
    out["month"] = ds[ok].dt.month
    return out


def _aggregate_full(raw_dir=config.RAW_DIR):
    """Una sola pasada por los CSV completos: geografías (para el mapeo) y conteos por año/mes/país/geo + histograma de precios."""
    from .data import DTYPES, USECOLS
    geo_parts, mes_parts, pais_parts, hist = [], [], [], {}
    for year, fname in config.RAW_FILES.items():
        h = np.zeros(len(PRICE_BINS) - 1)
        for chunk in pd.read_csv(raw_dir / fname, usecols=USECOLS, dtype=DTYPES, chunksize=500_000, low_memory=False):
            # mapeo: sobre TODAS las filas (incluye inválidas), como el script de referencia del repo
            cr = pd.to_numeric(chunk["count_repeated"], errors="coerce").fillna(0)
            geo_parts.append(chunk.assign(count_repeated=cr).groupby(GEO_COLS, dropna=False)
                             .agg(row_count=("city", "size"), demand_weight=("count_repeated", "sum")).reset_index())
            v = _valid(chunk)
            v = v[v["anio_archivo"] == year]
            mes_parts.append(v.groupby("month").size().rename("n").reset_index().assign(anio=year))
            pais_parts.append(v.groupby(v["country_code"].str.upper()).size().rename("n").reset_index().assign(anio=year))
            h += np.histogram(np.log(v["avg_price_average"]), bins=PRICE_BINS)[0]
            geo_valid = v.groupby(GEO_COLS, dropna=False).size().rename("n_valid").reset_index().assign(anio=year)
            geo_parts[-1] = geo_parts[-1].merge(geo_valid.drop(columns="anio"), on=GEO_COLS, how="left")
            geo_parts[-1]["anio"] = year
        hist[year] = h
    geo = pd.concat(geo_parts, ignore_index=True)
    geo["n_valid"] = geo["n_valid"].fillna(0)
    geo = geo.groupby(GEO_COLS + ["anio"], dropna=False)[["row_count", "demand_weight", "n_valid"]].sum().reset_index()
    mes = pd.concat(mes_parts).groupby(["anio", "month"])["n"].sum().reset_index()
    pais = pd.concat(pais_parts).groupby(["anio", "country_code"])["n"].sum().reset_index()
    return geo, mes, pais, hist


def _hist_quantiles(h: np.ndarray) -> list[float]:
    cdf = np.cumsum(h) / h.sum()
    centers = np.exp((PRICE_BINS[:-1] + PRICE_BINS[1:]) / 2)
    return [float(centers[np.searchsorted(cdf, q)]) for q in QS]


def run(raw_dir=config.RAW_DIR, out_dir=config.OUTPUTS_DIR / "diagnosticos"):
    out_dir.mkdir(parents=True, exist_ok=True)
    geo, mes, pais, hist = _aggregate_full(raw_dir)

    # ---------------- 1. Cobertura del mapeo (2024 + 2025, dataset completo) ----------------
    mapper = DestinationMapper(config.MAPPING_PATH)
    g_all = geo.groupby(GEO_COLS, dropna=False)[["row_count", "demand_weight", "n_valid"]].sum().reset_index()
    mapped = pd.DataFrame([mapper.map_one(*r) for r in g_all[GEO_COLS].itertuples(index=False, name=None)])
    g_all = pd.concat([g_all, mapped], axis=1)
    geo = geo.merge(g_all[GEO_COLS + ["destination_final", "is_mapped", "match_level"]], on=GEO_COLS, how="left")

    def cov(x, label):
        return [
            {"alcance": label, "metrica": "filas", "mapeado": x.loc[x.is_mapped, "row_count"].sum(), "total": x["row_count"].sum()},
            {"alcance": label, "metrica": "demanda (count_repeated)", "mapeado": x.loc[x.is_mapped, "demand_weight"].sum(), "total": x["demand_weight"].sum()},
            {"alcance": label, "metrica": "geografías únicas", "mapeado": int(x["is_mapped"].sum()), "total": len(x)},
        ]
    resumen = pd.DataFrame(cov(g_all, "2024+2025"))
    resumen["cobertura_pct"] = 100 * resumen["mapeado"] / resumen["total"]
    resumen.to_csv(out_dir / "cobertura_mapeo_resumen.csv", index=False)

    por_nivel = (g_all.groupby("match_level")
                 .agg(filas=("row_count", "sum"), demanda=("demand_weight", "sum"), geografias=("city", "size"))
                 .assign(pct_filas=lambda d: 100 * d["filas"] / d["filas"].sum(),
                         pct_demanda=lambda d: 100 * d["demanda"] / d["demanda"].sum())
                 .sort_values("demanda", ascending=False).reset_index())
    por_nivel.to_csv(out_dir / "cobertura_mapeo_por_nivel.csv", index=False)

    no_map = (g_all[~g_all["is_mapped"]].sort_values("demand_weight", ascending=False)
              .head(30)[GEO_COLS + ["row_count", "demand_weight"]])
    no_map.to_csv(out_dir / "cobertura_mapeo_no_mapeados_top.csv", index=False)

    # ---------------- 2. Representatividad de la muestra ----------------
    rows_mes, rows_pais, rows_dest, rows_precio, resumen_rep = [], [], [], [], []
    for year in config.RAW_FILES:
        s = pd.read_parquet(config.INTERIM_DIR / f"muestra_{year}.parquet",
                            columns=["month", "country_code", "destination_final", "price", "avg_price_average"])
        # mes
        full_m = mes[mes.anio == year].set_index("month")["n"]
        samp_m = s["month"].value_counts()
        dm = pd.DataFrame({"pct_total": 100 * full_m / full_m.sum(), "pct_muestra": 100 * samp_m / samp_m.sum()}).fillna(0)
        dm["dif_pp"] = dm["pct_muestra"] - dm["pct_total"]
        rows_mes.append(dm.reset_index(names="mes").assign(anio=year))
        # país (top 15 del total)
        full_p = pais[pais.anio == year].set_index("country_code")["n"]
        samp_p = s["country_code"].str.upper().value_counts()
        top = full_p.sort_values(ascending=False).head(15).index
        dp = pd.DataFrame({"pct_total": 100 * full_p / full_p.sum(), "pct_muestra": 100 * samp_p / samp_p.sum()}).fillna(0).loc[top]
        dp["dif_pp"] = dp["pct_muestra"] - dp["pct_total"]
        rows_pais.append(dp.reset_index(names="pais").assign(anio=year))
        # destino (top 20 del total, filas válidas)
        full_d = geo[geo.anio == year].groupby("destination_final")["n_valid"].sum()
        samp_d = s["destination_final"].value_counts()
        topd = full_d.sort_values(ascending=False).head(20).index
        names = g_all.drop_duplicates("destination_final").set_index("destination_final")["destination_name"]
        dd = pd.DataFrame({"pct_total": 100 * full_d / full_d.sum(), "pct_muestra": 100 * samp_d / samp_d.sum()}).fillna(0).loc[topd]
        dd["dif_pp"] = dd["pct_muestra"] - dd["pct_total"]
        dd.insert(0, "destino", names.reindex(dd.index).values)
        rows_dest.append(dd.reset_index(names="destination_final").assign(anio=year))
        # precio
        qf = _hist_quantiles(hist[year])
        qm = list(s["avg_price_average"].quantile(QS).values)
        rows_precio += [{"anio": year, "cuantil": q, "total_aprox": f, "muestra": mm, "dif_pct": 100 * (mm / f - 1)}
                        for q, f, mm in zip(QS, qf, qm)]
        resumen_rep.append({
            "anio": year, "filas_validas_total": int(full_m.sum()), "filas_muestra": len(s),
            "fraccion_muestra_pct": 100 * len(s) / full_m.sum(),
            "max_dif_mes_pp": dm["dif_pp"].abs().max(), "max_dif_pais_top15_pp": dp["dif_pp"].abs().max(),
            "max_dif_destino_top20_pp": dd["dif_pp"].abs().max(),
            "max_dif_cuantil_precio_pct": max(abs(r["dif_pct"]) for r in rows_precio if r["anio"] == year),
        })
    pd.concat(rows_mes).to_csv(out_dir / "representatividad_mes.csv", index=False)
    pd.concat(rows_pais).to_csv(out_dir / "representatividad_pais.csv", index=False)
    pd.concat(rows_dest).to_csv(out_dir / "representatividad_destino.csv", index=False)
    pd.DataFrame(rows_precio).to_csv(out_dir / "representatividad_precio.csv", index=False)
    pd.DataFrame(resumen_rep).to_csv(out_dir / "representatividad_resumen.csv", index=False)
    log.info("Diagnósticos guardados en %s", out_dir)
