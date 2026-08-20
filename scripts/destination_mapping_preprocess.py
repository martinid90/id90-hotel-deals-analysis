from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

import pandas as pd


GEO_COLS = ["country_code", "country", "state", "city"]

US_STATE_CODES = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
    "district of columbia": "DC",
}

US_TERRITORY_COUNTRY_CODES = {
    "puerto rico": "PR",
    "guam": "GU",
    "united states virgin islands": "VI",
    "virgin islands": "VI",
}


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value)
    text = "".join(
        ch
        for ch in unicodedata.normalize("NFD", text)
        if unicodedata.category(ch) != "Mn"
    )
    return re.sub(r"\s+", " ", text).strip().casefold()


def _series_reference(country: pd.Series, state: pd.Series, city: pd.Series) -> pd.Series:
    return (
        country.fillna("")
        + " - "
        + state.fillna("")
        + " - "
        + city.fillna("")
    ).map(clean_text)


def _series_country_city(country: pd.Series, city: pd.Series) -> pd.Series:
    return (country.fillna("") + " - " + city.fillna("")).map(clean_text)


def _strip_cdp_suffix(city: object) -> str | None:
    if pd.isna(city):
        return None
    raw = str(city).strip()
    stripped = re.sub(r"\s+CDP$", "", raw, flags=re.IGNORECASE).strip()
    if stripped and clean_text(stripped) != clean_text(raw):
        return stripped
    return None


def apply_destination_mapping_preprocessed(
    df: pd.DataFrame,
    mapping_df: pd.DataFrame,
    *,
    use_usa_alias: bool = True,
    recode_us_territories: bool = True,
    use_cdp_city_variant: bool = True,
    use_non_us_state_as_place: bool = True,
) -> pd.DataFrame:
    """Apply destination_with_nearest.csv with conservative preprocessing.

    This mirrors the recommender lookup style where possible:
    reference + city must match the lookup. Extra rules are explicit and
    labelled in match_level so downstream analysis can audit them.
    """

    missing_geo = set(GEO_COLS) - set(df.columns)
    if missing_geo:
        raise ValueError(f"Input df missing geography columns: {sorted(missing_geo)}")

    missing_mapping = {
        "reference",
        "city",
        "nearest_destination_id",
        "nearest_destination_name",
    } - set(mapping_df.columns)
    if missing_mapping:
        raise ValueError(f"Mapping df missing columns: {sorted(missing_mapping)}")

    mapping = mapping_df.copy()
    mapping["ref_clean"] = mapping["reference"].map(clean_text)
    mapping["city_clean"] = mapping["city"].map(clean_text)
    lookup = (
        mapping.drop_duplicates(["ref_clean", "city_clean"])
        .set_index(["ref_clean", "city_clean"])[
            ["nearest_destination_id", "nearest_destination_name"]
        ]
    )

    geo = df[GEO_COLS].drop_duplicates().copy()
    geo["cc"] = geo["country_code"].fillna("").str.upper()
    geo["state_clean"] = geo["state"].map(clean_text)
    geo["city_clean"] = geo["city"].map(clean_text)

    if recode_us_territories:
        territory_cc = geo["state_clean"].map(US_TERRITORY_COUNTRY_CODES)
        geo.loc[territory_cc.notna(), "cc"] = territory_cc[territory_cc.notna()]

    geo["state_code"] = geo["state_clean"].map(US_STATE_CODES)
    geo["cc_usa_alias"] = geo["cc"].where(geo["cc"].ne("US"), "USA")

    geo["nearest_destination_id"] = pd.NA
    geo["nearest_destination_name"] = pd.NA
    geo["match_level"] = "no_match"

    def fill_from_pair(ref: pd.Series, city: pd.Series, label: str, mask: pd.Series | None = None) -> None:
        idx = pd.MultiIndex.from_arrays([ref, city])
        matched = pd.DataFrame(index=geo.index)
        matched["nearest_destination_id"] = idx.map(lookup["nearest_destination_id"])
        matched["nearest_destination_name"] = idx.map(lookup["nearest_destination_name"])
        new_match = geo["nearest_destination_id"].isna() & matched["nearest_destination_id"].notna()
        if mask is not None:
            new_match &= mask
        geo.loc[new_match, "nearest_destination_id"] = matched.loc[new_match, "nearest_destination_id"]
        geo.loc[new_match, "nearest_destination_name"] = matched.loc[new_match, "nearest_destination_name"]
        geo.loc[new_match, "match_level"] = label

    countries = ["cc"]
    if use_usa_alias:
        countries.append("cc_usa_alias")

    for country_col in countries:
        fill_from_pair(
            _series_reference(geo[country_col], geo["state_code"], geo["city"]),
            geo["city_clean"],
            f"{country_col}_state_code_city",
        )
        fill_from_pair(
            _series_reference(geo[country_col], geo["state"], geo["city"]),
            geo["city_clean"],
            f"{country_col}_state_name_city",
        )
        fill_from_pair(
            _series_country_city(geo[country_col], geo["city"]),
            geo["city_clean"],
            f"{country_col}_country_city",
        )

    if use_cdp_city_variant:
        cdp_city = geo["city"].map(_strip_cdp_suffix)
        has_cdp_variant = cdp_city.notna()
        cdp_clean = cdp_city.map(clean_text)
        for country_col in countries:
            fill_from_pair(
                _series_reference(geo[country_col], geo["state_code"], cdp_city.fillna("")),
                cdp_clean,
                f"{country_col}_cdp_state_code_city",
                has_cdp_variant,
            )
            fill_from_pair(
                _series_reference(geo[country_col], geo["state"], cdp_city.fillna("")),
                cdp_clean,
                f"{country_col}_cdp_state_name_city",
                has_cdp_variant,
            )
            fill_from_pair(
                _series_country_city(geo[country_col], cdp_city.fillna("")),
                cdp_clean,
                f"{country_col}_cdp_country_city",
                has_cdp_variant,
            )

    if use_non_us_state_as_place:
        non_us = geo["cc"].ne("US")
        fill_from_pair(
            _series_country_city(geo["cc"], geo["state"]),
            geo["state_clean"],
            "non_us_state_as_place",
            non_us,
        )

    result = df.merge(
        geo[
            GEO_COLS
            + ["nearest_destination_id", "nearest_destination_name", "match_level"]
        ],
        on=GEO_COLS,
        how="left",
    )
    result["is_mapped"] = result["nearest_destination_id"].notna()
    result["destination_final"] = result["nearest_destination_id"].fillna(result["city"])
    result["destination_name"] = result["nearest_destination_name"].fillna(result["city"])
    return result


def aggregate_historical_geographies(files: list[Path], chunksize: int = 500_000) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    usecols = GEO_COLS + ["count_repeated"]
    for file in files:
        for chunk in pd.read_csv(
            file,
            usecols=usecols,
            chunksize=chunksize,
            dtype={col: str for col in GEO_COLS},
            low_memory=False,
        ):
            parts.append(
                chunk.groupby(GEO_COLS, dropna=False)
                .agg(row_count=("city", "size"), demand_weight=("count_repeated", "sum"))
                .reset_index()
            )
    return (
        pd.concat(parts, ignore_index=True)
        .groupby(GEO_COLS, dropna=False)
        .agg(row_count=("row_count", "sum"), demand_weight=("demand_weight", "sum"))
        .reset_index()
    )


def coverage_tables(mapped_geo: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    total_rows = mapped_geo["row_count"].sum()
    total_demand = mapped_geo["demand_weight"].sum()
    mapped_rows = mapped_geo.loc[mapped_geo["is_mapped"], "row_count"].sum()
    mapped_demand = mapped_geo.loc[mapped_geo["is_mapped"], "demand_weight"].sum()

    summary = pd.DataFrame(
        [
            {
                "metric": "rows",
                "mapped": mapped_rows,
                "total": total_rows,
                "coverage_pct": mapped_rows / total_rows * 100,
            },
            {
                "metric": "demand_weight",
                "mapped": mapped_demand,
                "total": total_demand,
                "coverage_pct": mapped_demand / total_demand * 100,
            },
            {
                "metric": "unique_geographies",
                "mapped": int(mapped_geo["is_mapped"].sum()),
                "total": len(mapped_geo),
                "coverage_pct": mapped_geo["is_mapped"].mean() * 100,
            },
        ]
    )

    by_level = (
        mapped_geo.groupby("match_level", dropna=False)
        .agg(
            rows=("row_count", "sum"),
            demand_weight=("demand_weight", "sum"),
            unique_geographies=("city", "size"),
        )
        .assign(
            row_pct=lambda x: x["rows"] / total_rows * 100,
            demand_pct=lambda x: x["demand_weight"] / total_demand * 100,
        )
        .sort_values("demand_weight", ascending=False)
    )

    return summary, by_level


def top_unmatched(mapped_geo: pd.DataFrame, n: int = 30) -> pd.DataFrame:
    return (
        mapped_geo.loc[~mapped_geo["is_mapped"], GEO_COLS + ["row_count", "demand_weight"]]
        .sort_values("demand_weight", ascending=False)
        .head(n)
    )


def print_coverage(mapped_geo: pd.DataFrame) -> None:
    summary, by_level = coverage_tables(mapped_geo)
    rows = summary.set_index("metric")

    print("Coverage")
    for metric in ["rows", "demand_weight", "unique_geographies"]:
        mapped = rows.loc[metric, "mapped"]
        total = rows.loc[metric, "total"]
        pct = rows.loc[metric, "coverage_pct"]
        print(f"  {metric}: {mapped:,.0f} / {total:,.0f} = {pct:.3f}%")

    print("\nBy match_level")
    print(by_level.to_string())

    print("\nTop unmatched by demand")
    print(top_unmatched(mapped_geo).to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--mapping", type=Path, default=Path("data/destination_with_nearest.csv"))
    parser.add_argument("--pattern", default="datos_historicos_*.csv")
    args = parser.parse_args()

    files = sorted(args.data_dir.glob(args.pattern))
    if not files:
        raise SystemExit(f"No historical files found in {args.data_dir} with pattern {args.pattern}")

    geo = aggregate_historical_geographies(files)
    mapping = pd.read_csv(args.mapping, dtype={"nearest_destination_id": str, "reference": str, "city": str})
    mapped = apply_destination_mapping_preprocessed(geo, mapping)
    print_coverage(mapped)


if __name__ == "__main__":
    main()
