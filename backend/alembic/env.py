from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from florabase.auth.model import AuthSession, LoginThrottle, User
from florabase.botanical_identities.model import BotanicalIdentity
from florabase.botanical_profiles.model import BotanicalProfile
from florabase.core.config import get_settings
from florabase.db.base import Base
from florabase.events.model import Event
from florabase.external_botany.model import ExternalProviderCache, ExternalTaxonLink
from florabase.geographic_places.model import GeographicPlace
from florabase.locations.model import Location
from florabase.plants.model import Plant, PlantGroup
from florabase.provenance_sites.model import ProvenanceSite
from florabase.seed_lots.model import SeedLot
from florabase.sowings.model import Sowing
from florabase.suppliers.model import Supplier

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = Base.metadata

# Importing the mapping registers it with the shared metadata used by Alembic.
assert BotanicalIdentity.__table__.metadata is target_metadata
assert BotanicalProfile.__table__.metadata is target_metadata
assert ExternalTaxonLink.__table__.metadata is target_metadata
assert ExternalProviderCache.__table__.metadata is target_metadata
assert Supplier.__table__.metadata is target_metadata
assert Location.__table__.metadata is target_metadata
assert GeographicPlace.__table__.metadata is target_metadata
assert ProvenanceSite.__table__.metadata is target_metadata
assert SeedLot.__table__.metadata is target_metadata
assert Sowing.__table__.metadata is target_metadata
assert Plant.__table__.metadata is target_metadata
assert PlantGroup.__table__.metadata is target_metadata
assert Event.__table__.metadata is target_metadata
assert all(
    model.__table__.metadata is target_metadata for model in (User, AuthSession, LoginThrottle)
)


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
