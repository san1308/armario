from fastapi import APIRouter, Depends

from app.core.auth import usuario_actual
from app.models import Usuario
from app.schemas import UsuarioRead

router = APIRouter(tags=["usuario"])


@router.get("/yo", response_model=UsuarioRead)
def yo(usuario: Usuario = Depends(usuario_actual)):
    return UsuarioRead(id=usuario.id, email=usuario.email, nombre=usuario.nombre)
