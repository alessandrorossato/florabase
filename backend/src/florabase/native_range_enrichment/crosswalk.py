"""Reviewed literal WGSRPD/ISO crosswalk; absence never authorizes a fallback."""

from florabase.native_range_enrichment.schemas import SourceAssertion

CROSSWALK_VERSION = "wcvp15-wgsrpd2-cldr48.2.1-v1"
GEOGRAPHY_SOURCE = ("unicode_cldr", "48.2.1", "iso_3166_1_alpha_2")
# WGSRPD edition 2, tables 3/4/5. Each of these level-3 units has a single
# level-4 OO unit and an exact ISO counterpart. See docs/native-range-enrichment.md.
EQUIVALENT = {
    "BOL": "BO",
    "BUL": "BG",
    "CBD": "KH",
    "COS": "CR",
    "HUN": "HU",
    "LAO": "LA",
    "OMA": "OM",
    "PAR": "PY",
    "PER": "PE",
    "THA": "TH",
    "URU": "UY",
    "VIE": "VN",
}
# Display limitations; these are explicitly NOT applicable mappings.
SPLITS = {
    "CZE": ("CZ", "SK"),
    "BLT": ("EE", "LV", "LT"),
    "LBS": ("LB", "SY"),
}
PARTIAL = {"ITA", "SAR", "SIC", "FRA", "COR", "SPA", "BAL", "BZN", "BZS", "BZL", "BZE", "BZC"}


def classify(row: dict[str, str]) -> SourceAssertion:
    code = row["area_code_l3"]
    status = "native"
    if row["introduced"] == "1":
        status = "introduced"
    if row["extinct"] != "0" or row["location_doubtful"] != "0":
        status = "qualified"
    mapping = "unresolved"
    note = "No reviewed equivalent mapping. Source unit is retained without a canonical addition."
    if code in EQUIVALENT:
        mapping = "equivalent"
        note = "Reviewed level-3 / ISO equivalence."
    elif code in SPLITS:
        mapping = "unsupported_split"
        note = (
            f"Source unit spans {', '.join(SPLITS[code])}. No policy authorizes finer assertions."
        )
    elif code in PARTIAL:
        mapping = "partial"
        note = (
            "Source unit is a partial country or has separate islands. No rounding to ISO country."
        )
    if status != "native":
        note += " Introduced, extinct or doubtful evidence is context only."
    return SourceAssertion(
        assertion_id=row["plant_locality_id"],
        original=row,
        status=status,
        mapping=mapping,
        note=note,
    )
