from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class AttachmentResponse(BaseModel):
    id: UUID
    original_filename: str
    media_type: Literal["image/jpeg", "image/png", "image/webp"]
    byte_size: int
    sha256: str
    state: Literal["active", "pending_delete"]
    created_at: datetime

    @classmethod
    def from_model(cls, attachment: object) -> AttachmentResponse:
        return cls.model_validate(attachment, from_attributes=True)
