from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlmodel import Session

from app.core.auth import usuario_actual
from app.core.categorias import POR_SLUG, TEMPORADA_SLUGS, ZONA_SLUGS
from app.core.database import get_session
from app.models import Prenda, Usuario
from app.schemas import PrendaRead, PrendaUpdate
from app.services import almacen, prenda_service

router = APIRouter(prefix="/prendas", tags=["prendas"])

MAX_BYTES = 25 * 1024 * 1024  # 25 MB por foto


def _prenda(prenda_id: int, session: Session, usuario: Usuario) -> Prenda:
    p = prenda_service.obtener(session, usuario, prenda_id)
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prenda no encontrada.")
    return p


@router.get("/", response_model=list[PrendaRead])
def listar(
    zona: Optional[str] = None,
    categoria: Optional[str] = None,
    sin_clasificar: bool = False,
    temporada: Optional[str] = None,
    session: Session = Depends(get_session),
    usuario: Usuario = Depends(usuario_actual),
):
    if zona and zona not in ZONA_SLUGS:
        raise HTTPException(422, "Zona desconocida.")
    if temporada and temporada != "ninguna" and temporada not in TEMPORADA_SLUGS:
        raise HTTPException(422, "Temporada desconocida.")
    prendas = prenda_service.listar(session, usuario, zona, categoria, sin_clasificar, temporada)
    return [PrendaRead.desde(p) for p in prendas]


@router.post("/", response_model=list[PrendaRead], status_code=status.HTTP_201_CREATED)
def subir(
    fotos: list[UploadFile] = File(...),
    categoria: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    usuario: Usuario = Depends(usuario_actual),
):
    """Sube una o varias fotos. Cada una se convierte en una prenda que se procesa en segundo plano."""
    if categoria is not None and categoria not in POR_SLUG:
        raise HTTPException(422, "Categoría desconocida.")
    creadas = []
    for foto in fotos:
        data = foto.file.read()
        if len(data) > MAX_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"{foto.filename} pesa más de 25 MB.")
        try:
            p = prenda_service.crear_desde_foto(session, usuario, data, foto.filename, categoria)
        except ValueError as e:
            raise HTTPException(422, str(e)) from e
        creadas.append(PrendaRead.desde(p))
    return creadas


@router.get("/{prenda_id}", response_model=PrendaRead)
def detalle(prenda_id: int, session: Session = Depends(get_session), usuario: Usuario = Depends(usuario_actual)):
    return PrendaRead.desde(_prenda(prenda_id, session, usuario))


@router.patch("/{prenda_id}", response_model=PrendaRead)
def actualizar(
    prenda_id: int,
    datos: PrendaUpdate,
    session: Session = Depends(get_session),
    usuario: Usuario = Depends(usuario_actual),
):
    p = _prenda(prenda_id, session, usuario)
    return PrendaRead.desde(prenda_service.actualizar(session, p, datos))


@router.post("/{prenda_id}/reprocesar", response_model=PrendaRead)
def reprocesar(prenda_id: int, session: Session = Depends(get_session), usuario: Usuario = Depends(usuario_actual)):
    p = _prenda(prenda_id, session, usuario)
    return PrendaRead.desde(prenda_service.reprocesar(session, p))


@router.delete("/{prenda_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar(prenda_id: int, session: Session = Depends(get_session), usuario: Usuario = Depends(usuario_actual)):
    prenda_service.borrar(session, _prenda(prenda_id, session, usuario))


@router.get("/{prenda_id}/imagen/{tipo}")
def imagen(
    prenda_id: int,
    tipo: Literal["original", "sinfondo", "recorte", "mini"],
    session: Session = Depends(get_session),
    usuario: Usuario = Depends(usuario_actual),
):
    p = _prenda(prenda_id, session, usuario)
    ruta = almacen.ruta(p, tipo)
    if not ruta.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Imagen aún no disponible.")
    # El front pide siempre ?v=<version>, así que se puede cachear para siempre
    return FileResponse(
        ruta,
        media_type=almacen.media_type(tipo),
        headers={"Cache-Control": "private, max-age=31536000, immutable"},
    )
