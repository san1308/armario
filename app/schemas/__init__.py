from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.core.categorias import POR_SLUG, normalizar_temporadas, temporadas_de, zona_de
from app.models import EstadoPrenda, Prenda


def _validar_categoria(v: Optional[str]) -> Optional[str]:
    if v is not None and v not in POR_SLUG:
        raise ValueError(f"Categoría desconocida: {v}")
    return v


# ── Usuario ───────────────────────────────────────────────────────────────────
class UsuarioRead(BaseModel):
    id: int
    email: str
    nombre: str


# ── Catálogo ──────────────────────────────────────────────────────────────────
class CategoriaRead(BaseModel):
    slug: str
    nombre: str
    zona: str


class ZonaRead(BaseModel):
    slug: str
    nombre: str


class CatalogoRead(BaseModel):
    zonas: list[ZonaRead]
    categorias: list[CategoriaRead]
    temporadas: list[ZonaRead]


# ── Prenda ────────────────────────────────────────────────────────────────────
class PrendaRead(BaseModel):
    id: int
    categoria: Optional[str]
    zona: Optional[str]
    nombre: Optional[str]
    temporadas: list[str]
    estado: EstadoPrenda
    error: Optional[str]
    corte_auto: Optional[float]
    corte_manual: Optional[float]
    escala: float
    desplazamiento: float
    ancho: Optional[int]
    alto: Optional[int]
    version: int
    creada: datetime

    @classmethod
    def desde(cls, p: Prenda) -> "PrendaRead":
        datos = p.model_dump(exclude={"usuario_id", "nombre_archivo", "temporadas"})
        return cls(**datos, zona=zona_de(p.categoria), temporadas=temporadas_de(p.temporadas))


class PrendaUpdate(BaseModel):
    """Todos los campos opcionales; solo se aplican los enviados."""

    categoria: Optional[str] = None
    nombre: Optional[str] = Field(default=None, max_length=100)
    temporadas: Optional[list[str]] = None  # lista completa; [] = todo el año
    escala: Optional[float] = Field(default=None, ge=0.3, le=2.5)
    desplazamiento: Optional[float] = Field(default=None, ge=-0.5, le=0.5)
    # null explícito = volver al corte automático
    corte_manual: Optional[float] = Field(default=None, ge=0.0, le=0.9)

    _v_cat = field_validator("categoria")(_validar_categoria)

    @field_validator("temporadas")
    @classmethod
    def _v_temporadas(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is not None:
            normalizar_temporadas(v)  # lanza ValueError si hay alguna desconocida
        return v


# ── Conjunto ──────────────────────────────────────────────────────────────────
class ConjuntoBase(BaseModel):
    nombre: Optional[str] = Field(default=None, max_length=100)
    exterior_id: Optional[int] = None
    arriba_id: Optional[int] = None
    abajo_id: Optional[int] = None
    entera_id: Optional[int] = None


class ConjuntoCreate(ConjuntoBase):
    pass


class ConjuntoRead(ConjuntoBase):
    id: int
    creado: datetime
