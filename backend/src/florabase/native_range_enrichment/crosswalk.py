"""Reviewed literal WGSRPD/ISO crosswalk; absence never authorizes a fallback."""

from types import MappingProxyType

from florabase.native_range_enrichment.schemas import SourceAssertion

GEOGRAPHY_SOURCE = ("unicode_cldr", "48.2.1", "iso_3166_1_alpha_2")
CROSSWALK_VERSIONS = MappingProxyType(
    {
        "15": ("wcvp15-wgsrpd2-cldr48.2.1-v1", "wcvp15-wgsrpd2-cldr48.2.1-v2"),
        "16": ("wcvp16-wgsrpd2-cldr48.2.1-v1", "wcvp16-wgsrpd2-cldr48.2.1-v2"),
    }
)
# The eleven pairs shared by v1 and v2. See the WGSRPD evidence in the native-range runbook.
_RETAINED = {
    "BOL": "BO",
    "BUL": "BG",
    "CBD": "KH",
    "HUN": "HU",
    "LAO": "LA",
    "OMA": "OM",
    "PAR": "PY",
    "PER": "PE",
    "THA": "TH",
    "URU": "UY",
    "VIE": "VN",
}
_V1_EQUIVALENT = MappingProxyType(_RETAINED | {"COS": "CR"})
EQUIVALENT = MappingProxyType(
    _RETAINED
    | {
        "ALB": "AL",
        "BLR": "BY",
        "DEN": "DK",
        "GER": "DE",
        "ICE": "IS",
        "POL": "PL",
        "ROM": "RO",
        "SWE": "SE",
        "SWI": "CH",
    }
)


def frozen_equivalences(source_version: str, crosswalk_version: str) -> MappingProxyType[str, str]:
    historical, current = CROSSWALK_VERSIONS[source_version]
    if crosswalk_version == historical:
        return _V1_EQUIVALENT
    if crosswalk_version == current:
        return EQUIVALENT
    raise ValueError("Unreviewed crosswalk for this WCVP release")


# Display limitations; these are explicitly NOT applicable mappings.
SPLITS = {
    "CZE": "Source unit spans CZ, SK. No policy authorizes finer assertions.",
    "BLT": "Source unit spans Estonia, Latvia, Lithuania and Kaliningrad (part of Russia).",
    "FIN": "Source unit includes Finland and Åland, which have separate canonical places.",
    "LBS": "Source unit spans LB, SY. No policy authorizes finer assertions.",
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
        note = SPLITS[code]
    elif code == "COS":
        mapping = "partial"
        note = "Source unit excludes Cocos Island, which is part of Costa Rica."
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
