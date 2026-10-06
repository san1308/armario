from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def ahora() -> datetime:
    return datetime.now(timezone.utc)


class Usuario(SQLModel, table=True):
    __tablename__ = "usuario"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True, max_length=255)
    nombre: str = Field(max_length=100)
    creado: datetime = Field(default_factory=ahora)
