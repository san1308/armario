"""Catálogo fijo de zonas del probador y categorías de prenda.

Una *zona* es una franja del probador (dónde va la prenda en el cuerpo).
Una *categoría* es lo que es la prenda; cada categoría pertenece a una zona.
Añadir una categoría nueva es añadir una línea aquí (no requiere migración:
en BD se guarda el slug como texto).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Zona:
    slug: str
    nombre: str


@dataclass(frozen=True)
class Categoria:
    slug: str
    nombre: str
    zona: str


ZONAS: list[Zona] = [
    Zona("exterior", "Encima"),
    Zona("arriba", "Arriba"),
    Zona("abajo", "Abajo"),
    Zona("entera", "Vestidos"),
]

CATEGORIAS: list[Categoria] = [
    # Capa exterior
    Categoria("abrigo", "Abrigo", "exterior"),
    Categoria("chaqueta", "Chaqueta", "exterior"),
    Categoria("americana", "Americana", "exterior"),
    Categoria("rebeca", "Rebeca o kimono", "exterior"),
    Categoria("chaleco", "Chaleco", "exterior"),
    # Parte de arriba
    Categoria("camiseta", "Camiseta", "arriba"),
    Categoria("blusa", "Blusa o camisa", "arriba"),
    Categoria("top", "Top o tirantes", "arriba"),
    Categoria("jersey", "Jersey o sudadera", "arriba"),
    # Parte de abajo
    Categoria("pantalon", "Pantalón", "abajo"),
    Categoria("vaquero", "Vaquero", "abajo"),
    Categoria("falda", "Falda", "abajo"),
    Categoria("short", "Short o bermuda", "abajo"),
    # Pieza entera
    Categoria("vestido", "Vestido", "entera"),
    Categoria("mono", "Mono", "entera"),
]

POR_SLUG: dict[str, Categoria] = {c.slug: c for c in CATEGORIAS}
ZONA_SLUGS: set[str] = {z.slug for z in ZONAS}


def zona_de(categoria: str | None) -> str | None:
    if categoria is None:
        return None
    c = POR_SLUG.get(categoria)
    return c.zona if c else None
