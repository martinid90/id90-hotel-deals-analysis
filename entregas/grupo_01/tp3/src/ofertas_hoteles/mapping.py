"""Mapping de geografía cruda → destino canónico.

Es la misma lógica de referencia del repo (scripts/destination_mapping_preprocess.py
del repo), reorganizada como clase para poder construir el lookup UNA sola vez y
reusarlo en cada request de la API.

Cascada de claves (cada match queda trazado en `match_level`):
  1. país - state_code - ciudad   (US con código de estado)
  2. país - state - ciudad
  3. país - ciudad
  4. ídem con alias USA, territorios de EE.UU. y sufijo CDP
  5. fuera de EE.UU.: país - state como lugar (barrio/distrito → mercado mayor)
Si nada matchea → `no_match`, y el destino queda como clave cruda
`raw:<pais>|<state>|<ciudad>` (no se mezcla con destinos canónicos ni entre países).
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

GEO_COLS = ["country_code", "country", "state", "city"]

US_STATE_CODES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA",
    "colorado": "CO", "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV", "new hampshire": "NH",
    "new jersey": "NJ", "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD", "tennessee": "TN",
    "texas": "TX", "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC",
}
US_TERRITORY_COUNTRY_CODES = {
    "puerto rico": "PR", "guam": "GU", "united states virgin islands": "VI", "virgin islands": "VI",
}


def clean_text(value: object) -> str:
    """Minúsculas, sin acentos y sin espacios repetidos."""
    if value is None or (isinstance(value, float) and pd.isna(value)) or value is pd.NA:
        return ""
    text = "".join(ch for ch in unicodedata.normalize("NFD", str(value)) if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text).strip().casefold()


def _strip_cdp(city: str) -> str | None:
    if not city:
        return None
    stripped = re.sub(r"\s+CDP$", "", city.strip(), flags=re.IGNORECASE).strip()
    return stripped if stripped and clean_text(stripped) != clean_text(city) else None


class DestinationMapper:
    def __init__(self, mapping_path: Path | str):
        m = pd.read_csv(mapping_path, dtype=str)
        m["ref_clean"] = m["reference"].map(clean_text)
        m["city_clean"] = m["city"].map(clean_text)
        m = m.drop_duplicates(["ref_clean", "city_clean"])
        self.lookup = {
            (r, c): (i, n)
            for r, c, i, n in zip(m["ref_clean"], m["city_clean"], m["nearest_destination_id"], m["nearest_destination_name"])
        }

    def map_one(self, country_code, country, state, city) -> dict:
        cc = (country_code or "").strip().upper() if isinstance(country_code, str) else ""
        state = state if isinstance(state, str) else ""
        city = city if isinstance(city, str) else ""
        state_clean, city_clean = clean_text(state), clean_text(city)
        if state_clean in US_TERRITORY_COUNTRY_CODES:
            cc = US_TERRITORY_COUNTRY_CODES[state_clean]
        state_code = US_STATE_CODES.get(state_clean, "")
        countries = [("cc", cc)] + ([("cc_usa_alias", "USA")] if cc == "US" else [])

        def try_pair(ref: str, c_clean: str):
            return self.lookup.get((clean_text(ref), c_clean))

        candidates = []
        for tag, ctry in countries:
            candidates += [
                (f"{tag}_state_code_city", f"{ctry} - {state_code} - {city}", city_clean),
                (f"{tag}_state_name_city", f"{ctry} - {state} - {city}", city_clean),
                (f"{tag}_country_city", f"{ctry} - {city}", city_clean),
            ]
        cdp = _strip_cdp(city)
        if cdp:
            cdp_clean = clean_text(cdp)
            for tag, ctry in countries:
                candidates += [
                    (f"{tag}_cdp_state_code_city", f"{ctry} - {state_code} - {cdp}", cdp_clean),
                    (f"{tag}_cdp_state_name_city", f"{ctry} - {state} - {cdp}", cdp_clean),
                    (f"{tag}_cdp_country_city", f"{ctry} - {cdp}", cdp_clean),
                ]
        if cc != "US":
            candidates.append(("non_us_state_as_place", f"{cc} - {state}", state_clean))

        for level, ref, c_clean in candidates:
            # la clave state_code solo tiene sentido si hay state_code
            if "state_code" in level and not state_code:
                continue
            hit = try_pair(ref, c_clean)
            if hit is not None:
                return {"cc": cc or "??", "destination_final": str(hit[0]), "destination_name": hit[1],
                        "is_mapped": True, "match_level": level}
        raw_key = f"raw:{cc}|{state_clean}|{city_clean}"
        return {"cc": cc or "??", "destination_final": raw_key, "destination_name": city or state or "desconocido",
                "is_mapped": False, "match_level": "no_match"}

    def map_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Mapea solo las geografías únicas (rápido) y vuelve a unir."""
        geo = df[GEO_COLS].drop_duplicates().reset_index(drop=True)
        mapped = pd.DataFrame([self.map_one(*row) for row in geo[GEO_COLS].itertuples(index=False, name=None)])
        geo = pd.concat([geo, mapped], axis=1)
        out = df.merge(geo, on=GEO_COLS, how="left")
        return out
