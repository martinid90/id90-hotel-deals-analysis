"""Mapping de ciudades crudas a destinos canónicos.

Misma estrategia en cascada que `auxiliary_functions.apply_destination_mapping`
del TP2 (referencia del docente). La diferencia es que el catálogo se indexa
una sola vez en `DestinationMapper`, así la API no lo reconstruye por request.
"""

import re
import unicodedata

import pandas as pd

from . import config

US_STATE_CODES = {
    'alabama': 'al', 'alaska': 'ak', 'arizona': 'az', 'arkansas': 'ar', 'california': 'ca',
    'colorado': 'co', 'connecticut': 'ct', 'delaware': 'de', 'florida': 'fl', 'georgia': 'ga',
    'hawaii': 'hi', 'idaho': 'id', 'illinois': 'il', 'indiana': 'in', 'iowa': 'ia',
    'kansas': 'ks', 'kentucky': 'ky', 'louisiana': 'la', 'maine': 'me', 'maryland': 'md',
    'massachusetts': 'ma', 'michigan': 'mi', 'minnesota': 'mn', 'mississippi': 'ms', 'missouri': 'mo',
    'montana': 'mt', 'nebraska': 'ne', 'nevada': 'nv', 'new hampshire': 'nh', 'new jersey': 'nj',
    'new mexico': 'nm', 'new york': 'ny', 'north carolina': 'nc', 'north dakota': 'nd', 'ohio': 'oh',
    'oklahoma': 'ok', 'oregon': 'or', 'pennsylvania': 'pa', 'rhode island': 'ri', 'south carolina': 'sc',
    'south dakota': 'sd', 'tennessee': 'tn', 'texas': 'tx', 'utah': 'ut', 'vermont': 'vt',
    'virginia': 'va', 'washington': 'wa', 'west virginia': 'wv', 'wisconsin': 'wi', 'wyoming': 'wy',
    'district of columbia': 'dc', 'puerto rico': 'pr', 'guam': 'gu', 'virgin islands': 'vi'
}

US_TERRITORY_COUNTRY_CODES = {
    "puerto rico": "PR",
    "guam": "GU",
    "united states virgin islands": "VI",
    "virgin islands": "VI",
}

GEO_COLS = ['country_code', 'country', 'state', 'city']


def strip_accents(text):
    """Minúsculas, sin acentos y con espacios colapsados."""
    if pd.isna(text) or not isinstance(text, str):
        return ""
    normalized = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", normalized).strip().casefold()


def _strip_cdp_suffix(city):
    if pd.isna(city):
        return None
    raw = str(city).strip()
    stripped = re.sub(r"\s+CDP$", "", raw, flags=re.IGNORECASE).strip()
    if stripped and strip_accents(stripped) != strip_accents(raw):
        return stripped
    return None


def _series_reference(country, state, city):
    return (country.fillna("") + " - " + state.fillna("") + " - " + city.fillna("")).apply(strip_accents)


def _series_country_city(country, city):
    return (country.fillna("") + " - " + city.fillna("")).apply(strip_accents)


class DestinationMapper:
    """Asigna `destination_final` a cada combinación geográfica."""

    def __init__(self, mapping_df):
        mapping = mapping_df.copy()
        mapping['ref_clean'] = mapping['reference'].astype(str).apply(strip_accents)
        mapping['city_clean'] = mapping['city'].astype(str).apply(strip_accents)
        self.lookup = (
            mapping.drop_duplicates(['ref_clean', 'city_clean'])
            .set_index(['ref_clean', 'city_clean'])[['nearest_destination_id', 'nearest_destination_name']]
        )

    @classmethod
    def from_file(cls, path=None):
        path = path or config.MAPPING_FILE
        return cls(pd.read_csv(path, dtype={'nearest_destination_id': str}, low_memory=False))

    def _map_geo(self, geo):
        geo = geo.copy()
        for c in GEO_COLS:
            geo[c] = geo[c].astype("object").where(geo[c].notna(), None)
        geo['cc'] = geo['country_code'].fillna('').astype(str).str.upper()
        geo['state_clean'] = geo['state'].astype(str).apply(strip_accents)
        geo['city_clean'] = geo['city'].astype(str).apply(strip_accents)

        territory_cc = geo['state_clean'].map(US_TERRITORY_COUNTRY_CODES)
        geo.loc[territory_cc.notna(), 'cc'] = territory_cc[territory_cc.notna()]
        geo['state_code'] = geo['state_clean'].map(US_STATE_CODES)
        geo['cc_usa_alias'] = geo['cc'].where(geo['cc'].ne('US'), 'USA')

        geo['nearest_destination_id'] = pd.NA
        geo['nearest_destination_name'] = pd.NA
        geo['match_level'] = 'no_match'
        lookup = self.lookup

        def fill(ref, city, label, mask=None):
            idx = pd.MultiIndex.from_arrays([ref, city])
            mid = pd.Series(idx.map(lookup['nearest_destination_id']), index=geo.index)
            mname = pd.Series(idx.map(lookup['nearest_destination_name']), index=geo.index)
            new = geo['nearest_destination_id'].isna() & mid.notna()
            if mask is not None:
                new &= mask
            geo.loc[new, 'nearest_destination_id'] = mid[new]
            geo.loc[new, 'nearest_destination_name'] = mname[new]
            geo.loc[new, 'match_level'] = label

        fill(_series_reference(geo['cc'], geo['state_code'], geo['city']), geo['city_clean'], "cc_state_code_city")
        fill(_series_reference(geo['cc'], geo['state'], geo['city']), geo['city_clean'], "cc_state_name_city")
        fill(_series_country_city(geo['cc'], geo['city']), geo['city_clean'], "cc_country_city")

        has_usa = geo['cc_usa_alias'].ne(geo['cc'])
        if has_usa.any():
            fill(_series_reference(geo['cc_usa_alias'], geo['state_code'], geo['city']), geo['city_clean'],
                 "usa_alias_state_code_city", has_usa)
            fill(_series_reference(geo['cc_usa_alias'], geo['state'], geo['city']), geo['city_clean'],
                 "usa_alias_state_name_city", has_usa)
            fill(_series_country_city(geo['cc_usa_alias'], geo['city']), geo['city_clean'],
                 "usa_alias_country_city", has_usa)

        cdp_city = geo['city'].map(_strip_cdp_suffix)
        has_cdp = cdp_city.notna()
        cdp_clean = cdp_city.apply(strip_accents)
        fill(_series_reference(geo['cc'], geo['state_code'], cdp_city.fillna("")), cdp_clean,
             "cc_cdp_state_code_city", has_cdp)
        fill(_series_reference(geo['cc'], geo['state'], cdp_city.fillna("")), cdp_clean,
             "cc_cdp_state_name_city", has_cdp)
        fill(_series_country_city(geo['cc'], cdp_city.fillna("")), cdp_clean, "cc_cdp_country_city", has_cdp)

        # Fuera de EE.UU. la "city" suele ser un barrio y el "state" el mercado
        fill(_series_country_city(geo['cc'], geo['state']), geo['state_clean'], "non_us_state_as_place",
             geo['cc'].ne('US'))
        return geo

    def transform(self, df):
        """Agrega destination_final, destination_name, is_mapped y match_level."""
        df = df.copy()
        for c in GEO_COLS:
            if c not in df.columns:
                df[c] = None
        key = df[GEO_COLS].astype("object").fillna("")
        geo = key.drop_duplicates().copy()
        mapped = self._map_geo(geo.mask(geo.eq("")))
        mapped[GEO_COLS] = geo[GEO_COLS].values
        cols = ['nearest_destination_id', 'nearest_destination_name', 'match_level']
        res = key.merge(mapped[GEO_COLS + cols], on=GEO_COLS, how='left')
        res.index = df.index

        df['is_mapped'] = res['nearest_destination_id'].notna().values
        df['match_level'] = res['match_level'].fillna('no_match').values
        # Fallback geográfico 1: ciudad no mapeada -> se conserva como mercado propio
        # (prefijo con país para no mezclar ciudades homónimas de distintos países).
        city_key = "city:" + df['country_code'].fillna('??').astype(str).str.upper() + ":" + \
            df['city'].astype(str).apply(strip_accents)
        city_key = city_key.where(df['city'].notna(), pd.NA)
        df['destination_final'] = res['nearest_destination_id'].astype("object").values
        df['destination_final'] = df['destination_final'].where(df['is_mapped'], city_key)
        df['destination_name'] = res['nearest_destination_name'].astype("object").values
        df['destination_name'] = df['destination_name'].where(df['is_mapped'], df['city'])
        df['country_code'] = df['country_code'].astype("object").where(df['country_code'].notna(), pd.NA)
        df['country_code'] = df['country_code'].str.upper()
        return df
