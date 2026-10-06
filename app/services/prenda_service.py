from __future__ import annotations

from typing import Optional

from PIL import Image
from sqlmodel import Session, select

from app.core.categorias import CATEGORIAS, normalizar_temporadas
from app.models import Conjunto, EstadoPrenda, Prenda, Usuario
from app.schemas import PrendaUpdate
from app.services import almacen, procesado_service, recorte_service


def listar(session: Session, usuario: Usuario, zona: Optional[str] = None,
           categoria: Optional[str] = None, sin_clasificar: bool = False,
           temporada: Optional[str] = None) -> list[Prenda]:
    q = select(Prenda).where(Prenda.usuario_id == usuario.id)
    if temporada == "ninguna":
        q = q.where(Prenda.temporadas == "")
    elif temporada:
        # Coincidencia exacta del elemento dentro de la lista separada por comas
        q = q.where(("," + Prenda.temporadas + ",").contains(f",{temporada},"))  # type: ignore[operator]
    if sin_clasificar:
        q = q.where(Prenda.categoria.is_(None))  # type: ignore[union-attr]
    if categoria:
        q = q.where(Prenda.categoria == categoria)
    if zona:
        slugs = [c.slug for c in CATEGORIAS if c.zona == zona]
        q = q.where(Prenda.categoria.in_(slugs))  # type: ignore[union-attr]
    return list(session.exec(q.order_by(Prenda.creada.desc(), Prenda.id.desc())))  # type: ignore[attr-defined]


def obtener(session: Session, usuario: Usuario, prenda_id: int) -> Optional[Prenda]:
    p = session.get(Prenda, prenda_id)
    return p if p and p.usuario_id == usuario.id else None


def crear_desde_foto(session: Session, usuario: Usuario, data: bytes,
                     nombre_archivo: Optional[str] = None,
                     categoria: Optional[str] = None,
                     temporadas: Optional[list[str]] = None) -> Prenda:
    """Guarda la foto normalizada y encola el recorte. Lanza ValueError si no es imagen."""
    try:
        original = recorte_service.abrir_normalizada(data)
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"No se puede leer la imagen {nombre_archivo or ''}".strip()) from e
    prenda = Prenda(usuario_id=usuario.id, categoria=categoria, nombre_archivo=nombre_archivo,
                    temporadas=normalizar_temporadas(temporadas))
    session.add(prenda)
    session.commit()
    session.refresh(prenda)
    almacen.carpeta(prenda).mkdir(parents=True, exist_ok=True)
    original.save(almacen.ruta(prenda, "original"), "JPEG", quality=90)
    procesado_service.encolar(prenda.id)
    session.refresh(prenda)
    return prenda


def actualizar(session: Session, prenda: Prenda, datos: PrendaUpdate) -> Prenda:
    cambios = datos.model_dump(exclude_unset=True)
    if "temporadas" in cambios:
        cambios["temporadas"] = normalizar_temporadas(cambios["temporadas"])
    recortar_de_nuevo = "corte_manual" in cambios and cambios["corte_manual"] != prenda.corte_manual
    for campo, valor in cambios.items():
        setattr(prenda, campo, valor)
    if recortar_de_nuevo and prenda.estado == EstadoPrenda.lista:
        # Rápido (<1 s): parte del PNG sin fondo ya calculado, no vuelve a usar el modelo
        sinfondo = Image.open(almacen.ruta(prenda, "sinfondo"))
        procesado_service.guardar_recorte(prenda, sinfondo)
    session.add(prenda)
    session.commit()
    session.refresh(prenda)
    return prenda


def reprocesar(session: Session, prenda: Prenda) -> Prenda:
    prenda.estado = EstadoPrenda.pendiente
    session.add(prenda)
    session.commit()
    procesado_service.encolar(prenda.id)
    session.refresh(prenda)
    return prenda


def borrar(session: Session, prenda: Prenda) -> None:
    """Borra la prenda y sus ficheros. Los conjuntos que se queden vacíos también se borran."""
    usuario_id = prenda.usuario_id
    almacen.borrar(prenda)
    session.delete(prenda)
    session.commit()  # FK con ON DELETE SET NULL limpia las referencias en conjunto
    vacios = session.exec(
        select(Conjunto).where(
            Conjunto.usuario_id == usuario_id,
            Conjunto.exterior_id.is_(None), Conjunto.arriba_id.is_(None),  # type: ignore[union-attr]
            Conjunto.abajo_id.is_(None), Conjunto.entera_id.is_(None),  # type: ignore[union-attr]
        )
    ).all()
    for c in vacios:
        session.delete(c)
    session.commit()
