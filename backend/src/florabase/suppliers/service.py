from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from florabase.suppliers.model import Supplier
from florabase.suppliers.schemas import SupplierCreate, SupplierUpdate


def create_supplier(database: Session, payload: SupplierCreate) -> Supplier:
    supplier = Supplier(**payload.model_dump(mode="json"))
    database.add(supplier)
    database.flush()
    return supplier


def get_supplier(database: Session, supplier_id: UUID) -> Supplier | None:
    return database.get(Supplier, supplier_id)


def list_suppliers(database: Session) -> list[Supplier]:
    statement = select(Supplier).order_by(
        case((Supplier.retired_at.is_(None), 0), else_=1),
        func.lower(Supplier.name),
        Supplier.kind,
        Supplier.id,
    )
    return list(database.scalars(statement))


def update_supplier(database: Session, supplier: Supplier, payload: SupplierUpdate) -> Supplier:
    for field, value in payload.model_dump(mode="json").items():
        setattr(supplier, field, value)
    supplier.updated_at = datetime.now(UTC)
    database.flush()
    return supplier


def set_supplier_retired(database: Session, supplier: Supplier, *, retired: bool) -> Supplier:
    now = datetime.now(UTC)
    supplier.retired_at = now if retired else None
    supplier.updated_at = now
    database.flush()
    return supplier
