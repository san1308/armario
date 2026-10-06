from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel

from app.models.usuario import ahora


class EstadoPrenda(str, Enum):
    pendiente = "pendiente"     # subida, esperando a quitar el fondo
    procesando = "procesando"
    lista = "lista"
    error = "error"


class Prenda(SQLModel, table=True):
    __tablename__ = "prenda"

    id: Optional[int] = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True, ondelete="CASCADE")

    # Slug de app.core.categorias; None = sin clasificar
    categoria: Optional[str] = Field(default=None, index=True, max_length=30)
    nombre: Optional[str] = Field(default=None, max_length=100)

    estado: EstadoPrenda = Field(default=EstadoPrenda.pendiente)
    error: Optional[str] = Field(default=None, max_length=500)

    # Línea de corte superior (0-1 sobre la foto) para quitar la percha.
    # corte_auto la calcula el procesado; corte_manual la fija el usuario.
    corte_auto: Optional[float] = None
    corte_manual: Optional[float] = None

    # Ajuste de encaje en el probador
    escala: float = Field(default=1.0)
    desplazamiento: float = Field(default=0.0)  # fracción de la altura de la prenda

    # Tamaño del recorte final (para que el front calcule proporciones sin esperar a la imagen)
    ancho: Optional[int] = None
    alto: Optional[int] = None

    # Se incrementa cada vez que cambia la imagen: el front lo usa para invalidar caché
    version: int = Field(default=0)

    nombre_archivo: Optional[str] = Field(default=None, max_length=255)
    creada: datetime = Field(default_factory=ahora)
