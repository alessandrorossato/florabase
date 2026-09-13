from typing import Any, cast

from sqlalchemy import DateTime, Table

from florabase.attachments.model import ATTACHMENT_MAX_BYTES, Attachment


def test_attachment_model_is_narrow_and_constrained() -> None:
    table = cast(Table, Attachment.__table__)
    identifier_default = table.c.id.default
    assert identifier_default is not None
    identifier_factory = cast(Any, identifier_default).arg
    assert identifier_factory({}).version == 7
    assert table.c.storage_key.unique is True
    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone is True
    constraints = " ".join(
        str(item.sqltext) for item in table.constraints if hasattr(item, "sqltext")
    )
    assert str(ATTACHMENT_MAX_BYTES) in constraints
    assert "pending_delete" in constraints
    assert "image/webp" in constraints
    assert "sha256" not in table.c.storage_key.name
    assert not any(
        name in table.columns
        for name in (
            "botanical_identity_id",
            "seed_lot_id",
            "sowing_id",
            "plant_id",
            "plant_group_id",
            "event_id",
            "metadata",
        )
    )
