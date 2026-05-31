from sqlmodel import Session, create_engine

from .migration_bootstrap import bootstrap_legacy_database_for_alembic, run_alembic_migrations
from .settings import settings

DATABASE_URL = settings.database_url
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})


def create_db_and_tables() -> None:
    bootstrap_legacy_database_for_alembic(engine=engine, database_url=settings.database_url)
    run_alembic_migrations(database_url=settings.database_url)


def get_session():
    with Session(engine) as session:
        yield session
