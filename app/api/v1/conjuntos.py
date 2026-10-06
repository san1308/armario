from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.auth import usuario_actual
from app.core.database import get_session
from app.models import Usuario
from app.schemas import ConjuntoCreate, ConjuntoRead
from app.services import conjunto_service

router = APIRouter(prefix="/conjuntos", tags=["conjuntos"])


@router.get("/", response_model=list[ConjuntoRead])
def listar(session: Session = Depends(get_session), usuario: Usuario = Depends(usuario_actual)):
    return conjunto_service.listar(session, usuario)


@router.post("/", response_model=ConjuntoRead, status_code=status.HTTP_201_CREATED)
def crear(datos: ConjuntoCreate, session: Session = Depends(get_session), usuario: Usuario = Depends(usuario_actual)):
    try:
        return conjunto_service.crear(session, usuario, datos)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


@router.delete("/{conjunto_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar(conjunto_id: int, session: Session = Depends(get_session), usuario: Usuario = Depends(usuario_actual)):
    c = conjunto_service.obtener(session, usuario, conjunto_id)
    if c is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conjunto no encontrado.")
    conjunto_service.borrar(session, c)
