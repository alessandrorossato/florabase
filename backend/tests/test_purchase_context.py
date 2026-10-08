from datetime import UTC, datetime
from uuid import uuid7

import pytest
from pydantic import ValidationError

from florabase.orders.purchase_schemas import PurchaseApplyRequest, PurchasePreviewRequest


@pytest.mark.parametrize(
    "values",
    [
        {"seed_lot_id": uuid7()},
        {"expected_seed_lot_updated_at": datetime.now(UTC)},
        {"expected_order_updated_at": "2026-10-08T00:00:00"},
        {
            "context": {
                "acquisition_date": {"precision": "month", "year": 2026, "month": 10, "day": 1}
            }
        },
        {"context": {"total_price": "32.50"}},
        {"synchronize_all_lots": True},
    ],
)
def test_apply_rejects_missing_versions_invented_precision_and_extra_fields(
    values: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        PurchaseApplyRequest.model_validate(
            {"context": {}, "expected_order_updated_at": datetime.now(UTC), **values}
        )


def test_existing_draft_preview_requires_version_but_reverse_selector_reads_current() -> None:
    identifier = uuid7()
    assert PurchasePreviewRequest(seed_lot_id=identifier).context is None
    with pytest.raises(ValidationError, match="expected updated_at"):
        PurchasePreviewRequest.model_validate({"seed_lot_id": identifier, "context": {}})
    apply = PurchaseApplyRequest.model_validate(
        {"context": {}, "expected_order_updated_at": datetime.now(UTC)}
    )
    assert not apply.use_order_date
    assert not apply.use_order_supplier
