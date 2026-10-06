"""Cola de procesado en segundo plano.

Un único hilo de trabajo: en la Raspberry Pi el modelo ocupa ~0,5-1 GB de RAM y
usa todos los núcleos, así que procesar varias fotos a la vez no ganaría nada
y podría quedarse sin memoria. Las prendas pendientes se reencolan al arrancar,
así que un reinicio a mitad de una subida grande no deja nada a medias.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from PIL import Image
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import engine
from app.models import EstadoPrenda, Prenda
from app.services import almacen, recorte_service

logger = logging.getLogger(__name__)

_executor: ThreadPoolExecutor | None = None


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="recorte")
    return _executor


def encolar(prenda_id: int) -> None:
    if settings.procesar_en_segundo_plano:
        _get_executor().submit(procesar_prenda, prenda_id)
    else:
        procesar_prenda(prenda_id)


def guardar_recorte(prenda: Prenda, sinfondo: Image.Image) -> None:
    """Genera recorte + miniatura desde `sinfondo` y actualiza la prenda (sin commit)."""
    res = recorte_service.recortar(sinfondo, prenda.corte_manual)
    res.imagen.save(almacen.ruta(prenda, "recorte"), "WEBP", quality=88, method=4)
    recorte_service.miniatura(res.imagen).save(almacen.ruta(prenda, "mini"), "WEBP", quality=80)
    prenda.corte_auto = round(res.corte_auto, 4)
    prenda.ancho, prenda.alto = res.imagen.size
    prenda.version += 1


def procesar_prenda(prenda_id: int) -> None:
    """Quita el fondo de la foto original y genera el recorte final."""
    with Session(engine) as session:
        prenda = session.get(Prenda, prenda_id)
        if prenda is None:
            return
        prenda.estado = EstadoPrenda.procesando
        session.add(prenda)
        session.commit()
        try:
            original = Image.open(almacen.ruta(prenda, "original"))
            sinfondo = recorte_service.quitar_fondo(original)
            sinfondo.save(almacen.ruta(prenda, "sinfondo"), "PNG", optimize=False, compress_level=3)
            guardar_recorte(prenda, sinfondo)
            prenda.estado = EstadoPrenda.lista
            prenda.error = None
        except Exception as e:  # noqa: BLE001
            logger.exception("Error procesando prenda %s", prenda_id)
            prenda.estado = EstadoPrenda.error
            prenda.error = str(e)[:500]
        session.add(prenda)
        session.commit()
        logger.info("Prenda %s → %s", prenda_id, prenda.estado.value)


def reencolar_pendientes() -> int:
    with Session(engine) as session:
        ids = session.exec(
            select(Prenda.id).where(
                Prenda.estado.in_([EstadoPrenda.pendiente, EstadoPrenda.procesando])  # type: ignore[attr-defined]
            )
        ).all()
    for pid in ids:
        encolar(pid)
    if ids:
        logger.info("Reencoladas %d prendas pendientes.", len(ids))
    return len(ids)


def apagar() -> None:
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=False, cancel_futures=True)
        _executor = None
