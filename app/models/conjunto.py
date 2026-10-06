from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.models.usuario import ahora


class Conjunto(SQLModel, table=True):
    """Combinación guardada. Una columna por zona del probador."""

    __tablename__ = "conjunto"

    id: Optional[int] = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True, ondelete="CASCADE")
    nombre: Optional[str] = Field(default=None, max_length=100)

    exterior_id: Optional[int] = Field(default=None, foreign_key="prenda.id", ondelete="SET NULL")
    arriba_id: Optional[int] = Field(default=None, foreign_key="prenda.id", ondelete="SET NULL")
    abajo_id: Optional[int] = Field(default=None, foreign_key="prenda.id", ondelete="SET NULL")
    entera_id: Optional[int] = Field(default=None, foreign_key="prenda.id", ondelete="SET NULL")

    creado: datetime = Field(default_factory=ahora)
