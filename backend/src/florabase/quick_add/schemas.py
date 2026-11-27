"""QUICK-ADD-001: one request that adds a Plant or PlantGroup with its botanical identity."""

from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from florabase.botanical_identities.schemas import BotanicalIdentityCreate
from florabase.plants.model import DirectOriginKind
from florabase.plants.schemas import PlantGroupQuantity
from florabase.seed_lots.schemas import PartialDate


class QuickAddWfoChoice(BaseModel):
    """A WFO name picked from the local index suggestions for a new identity."""

    model_config = ConfigDict(extra="forbid")
    source_taxon_id: str = Field(pattern=r"^wfo-[0-9]{10}$")


class QuickAddNewIdentity(BotanicalIdentityCreate):
    wfo: QuickAddWfoChoice | None = None


class QuickAddIdentity(BaseModel):
    """Exactly one of an existing identity or a new one (reused when it already exists)."""

    model_config = ConfigDict(extra="forbid")
    existing_id: UUID | None = None
    new: QuickAddNewIdentity | None = None

    @model_validator(mode="after")
    def exactly_one(self) -> Self:
        if (self.existing_id is None) == (self.new is None):
            raise ValueError("identity_choice: give either existing_id or new")
        return self


class QuickAddRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    identity: QuickAddIdentity
    material: Literal["plant", "plant_group"] = "plant"
    quantity: PlantGroupQuantity | None = None
    label: str | None = Field(default=None, max_length=255)
    location_id: UUID | None = None
    supplier_id: UUID | None = None
    direct_origin_kind: DirectOriginKind = DirectOriginKind.UNKNOWN
    collection_entry_date: PartialDate | None = None
    notes: str | None = Field(default=None, max_length=20_000)

    @model_validator(mode="after")
    def quantity_only_for_groups(self) -> Self:
        if self.material == "plant" and self.quantity is not None:
            raise ValueError("quantity: only a Plant group has a quantity")
        if self.quantity is not None and self.quantity.value == 0:
            raise ValueError("quantity: a new active group needs at least one plant")
        return self


class QuickAddResponse(BaseModel):
    record_kind: Literal["plant", "plant_group"]
    record_id: UUID
    identity_id: UUID
    identity_display_label: str
    identity_created: bool
    wfo_linked: bool
