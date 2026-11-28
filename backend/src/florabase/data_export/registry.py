"""Every database table is either exported (``TABLES``) or excluded with a reason (``EXCLUDED``).

The contract tests compare both lists with ``Base.metadata`` and with the migrated database, so a
new table or a new column fails CI until it is classified here. A new collection table normally
needs only one ``ExportTable(...)`` line: columns, partial dates and label columns are derived.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


@dataclass(frozen=True)
class ExportTable:
    table: str
    # Columns not written to the CSV, each with the reason.
    dropped: Mapping[str, str] = field(default_factory=dict)
    # Export only rows referenced by other exported tables (and their ancestors).
    referenced_only: bool = False

    @property
    def file(self) -> str:
        return f"{self.table}.csv"


_PROVIDER_COPY = "copied provider data; the export keeps provider ids only"
_OWNER = "user account id; the owner's display name is exported instead"

TABLES: tuple[ExportTable, ...] = (
    ExportTable("application_settings"),
    ExportTable("botanical_identities"),
    ExportTable("botanical_identity_names"),
    ExportTable("botanical_identity_reconciliations", {"actor_user_id": _OWNER}),
    ExportTable("botanical_profiles"),
    ExportTable("botanical_profile_native_ranges"),
    ExportTable(
        "external_taxon_links",
        dict.fromkeys(
            (
                "scientific_name",
                "canonical_name",
                "authorship",
                "accepted_name",
                "kingdom",
                "phylum",
                "class_name",
                "order_name",
                "family",
                "genus",
                "refresh_error",
            ),
            _PROVIDER_COPY,
        ),
    ),
    ExportTable("wfo_links", {"evidence": _PROVIDER_COPY}),
    ExportTable(
        "wcvp_links",
        {"taxon": _PROVIDER_COPY, "source": _PROVIDER_COPY, "identity_snapshot": _PROVIDER_COPY},
    ),
    ExportTable("geographic_places", referenced_only=True),
    ExportTable("provenance_sites"),
    ExportTable("locations"),
    ExportTable("suppliers"),
    ExportTable("orders"),
    ExportTable("seed_lots"),
    ExportTable("sowings"),
    ExportTable("germination_observations"),
    ExportTable("plant_groups"),
    ExportTable("plants"),
    ExportTable(
        "events",
        {"reversed_operation_receipt_id": "points to an internal undo receipt (excluded table)"},
    ),
    ExportTable("event_measurement_corrections"),
    ExportTable("vegetative_lots"),
    ExportTable("propagation_attempts"),
    ExportTable("rooting_observations"),
    ExportTable("harvests"),
    ExportTable("harvest_items"),
    ExportTable("harvest_material_inventory"),
    ExportTable("harvest_material_dispositions"),
    ExportTable("harvest_seed_lot_conversions"),
    ExportTable("scheduled_activities"),
    ExportTable("saved_views", {"owner_id": _OWNER}),
    ExportTable("attachments", {"storage_key": "internal storage path"}),
    ExportTable("media_assets", {"copy_cleanup_attachment_id": "internal cleanup bookkeeping"}),
    ExportTable("record_media_links"),
    ExportTable("botanical_identity_cover_images"),
    ExportTable("collection_primary_photos"),
)

EXCLUDED: Mapping[str, str] = MappingProxyType(
    {
        "users": "accounts and password hashes; only display names appear as labels",
        "auth_sessions": "web and device sessions with token digests",
        "login_throttles": "login security state",
        "operation_receipts": "internal undo snapshots, not collection records",
        "external_provider_cache": "cached licensed provider payloads",
        "native_range_proposals": "provider evidence payloads; the applied ranges are exported",
        "native_range_applications": "provider evidence payloads; the applied ranges are exported",
        "native_range_revisions": "internal concurrency counter",
    }
)

# Raw tables outside the SQLAlchemy models (migration bookkeeping), checked against the database.
UNMODELLED: Mapping[str, str] = MappingProxyType(
    {
        "alembic_version": "migration bookkeeping; its revision is in manifest.json",
        "app_metadata": "installation bookkeeping",
    }
)

LINEAGE_EDGES_FILE = "lineage_edges.csv"
# Columns pointing at these tables get a readable ``<column>_label`` next to the UUID.
LABEL_TABLES = (
    "botanical_identities",
    "locations",
    "suppliers",
    "plants",
    "plant_groups",
    "seed_lots",
    "sowings",
    "vegetative_lots",
    "propagation_attempts",
    "harvests",
)


def classification_errors(table_names: set[str], *, database: bool = False) -> list[str]:
    """Every table must be exported or excluded exactly once; nothing may name a missing table."""
    exported = [entry.table for entry in TABLES]
    known = set(exported) | set(EXCLUDED) | (set(UNMODELLED) if database else set())
    errors = [
        f"{name}: add it to data_export.registry TABLES or EXCLUDED (with a reason)"
        for name in sorted(table_names - known)
    ]
    errors += [
        f"{name}: listed in the registry but not a table" for name in sorted(known - table_names)
    ]
    errors += [
        f"{name}: exported twice" for name in sorted({n for n in exported if exported.count(n) > 1})
    ]
    errors += [
        f"{name}: both exported and excluded" for name in sorted(set(exported) & set(EXCLUDED))
    ]
    return errors
