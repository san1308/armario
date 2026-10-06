import sqlite3
from collections.abc import Generator

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    echo=settings.debug,
)


@event.listens_for(Engine, "connect")
def set_sqlite_pragmas(dbapi_connection, connection_record):
    """Activa WAL, sincronización relajada y foreign keys en cada conexión SQLite."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def create_db_tables() -> None:
    """Crea tablas si no existen. Solo para pruebas rápidas; en producción usa Alembic."""
    SQLModel.metadata.create_all(engine)
