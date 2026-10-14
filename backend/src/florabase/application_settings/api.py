from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from florabase.application_settings.model import ApplicationSettings
from florabase.application_settings.schemas import ApplicationSettingsValue
from florabase.auth.dependencies import (
    AuthenticatedActor,
    require_authenticated_actor,
    require_csrf,
)
from florabase.db.session import get_database_session

router = APIRouter(prefix="/application-settings", tags=["application-settings"])
Database = Annotated[Session, Depends(get_database_session)]
Reader = Annotated[AuthenticatedActor, Depends(require_authenticated_actor)]
Writer = Annotated[AuthenticatedActor, Depends(require_csrf)]


@router.get("", response_model=ApplicationSettingsValue, operation_id="getApplicationSettings")
def read(actor: Reader, database: Database) -> ApplicationSettingsValue:
    row = database.get(ApplicationSettings, 1)
    return ApplicationSettingsValue.model_validate(
        {
            "public_qr_base_url": row.public_qr_base_url if row else None,
            "default_label_preset": row.default_label_preset if row else "medium",
        }
    )


@router.put("", response_model=ApplicationSettingsValue, operation_id="saveApplicationSettings")
def save(
    payload: ApplicationSettingsValue, actor: Writer, database: Database
) -> ApplicationSettingsValue:
    # Atomic singleton upsert handles concurrent first saves. The session dependency commits.
    values = payload.model_dump()
    database.execute(
        insert(ApplicationSettings)
        .values(id=1, **values)
        .on_conflict_do_update(index_elements=[ApplicationSettings.id], set_=values)
    )
    return payload
