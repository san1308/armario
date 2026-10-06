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

# Temporadas: una prenda puede tener varias (p. ej. verano + entretiempo).
# Una prenda sin ninguna se considera "para todo el año" en el probador.
TEMPORADAS: list[Zona] = [
    Zona("verano", "Verano"),
    Zona("entretiempo", "Entretiempo"),
    Zona("invierno", "Invierno"),
]
TEMPORADA_SLUGS: list[str] = [t.slug for t in TEMPORADAS]

POR_SLUG: dict[str, Categoria] = {c.slug: c for c in CATEGORIAS}
ZONA_SLUGS: set[str] = {z.slug for z in ZONAS}


def normalizar_temporadas(valores: list[str] | None) -> str:
    """Lista → texto ordenado y sin duplicados para guardar en BD ("verano,entretiempo")."""
    vistos = set(valores or [])
    desconocidas = vistos - set(TEMPORADA_SLUGS)
    if desconocidas:
        raise ValueError(f"Temporada desconocida: {', '.join(sorted(desconocidas))}")
    return ",".join(t for t in TEMPORADA_SLUGS if t in vistos)


def temporadas_de(texto: str | None) -> list[str]:
    return [t for t in (texto or "").split(",") if t]


def zona_de(categoria: str | None) -> str | None:
    if categoria is None:
        return None
    c = POR_SLUG.get(categoria)
    return c.zona if c else None
