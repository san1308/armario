from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from app.models import Conjunto, Prenda, Usuario
from app.schemas import ConjuntoCreate

CAMPOS_PRENDA = ("exterior_id", "arriba_id", "abajo_id", "entera_id")


def listar(session: Session, usuario: Usuario) -> list[Conjunto]:
    q = select(Conjunto).where(Conjunto.usuario_id == usuario.id)
    return list(session.exec(q.order_by(Conjunto.creado.desc(), Conjunto.id.desc())))  # type: ignore[attr-defined]


def obtener(session: Session, usuario: Usuario, conjunto_id: int) -> Optional[Conjunto]:
    c = session.get(Conjunto, conjunto_id)
    return c if c and c.usuario_id == usuario.id else None


def crear(session: Session, usuario: Usuario, datos: ConjuntoCreate) -> Conjunto:
    """Valida que las prendas existan y sean del usuario. Lanza ValueError si no."""
    ids = [getattr(datos, c) for c in CAMPOS_PRENDA if getattr(datos, c) is not None]
    if not ids:
        raise ValueError("Un conjunto necesita al menos una prenda.")
    for pid in ids:
        p = session.get(Prenda, pid)
        if p is None or p.usuario_id != usuario.id:
            raise ValueError(f"La prenda {pid} no existe.")
    conjunto = Conjunto(usuario_id=usuario.id, **datos.model_dump())
    session.add(conjunto)
    session.commit()
    session.refresh(conjunto)
    return conjunto


def borrar(session: Session, conjunto: Conjunto) -> None:
    session.delete(conjunto)
    session.commit()
