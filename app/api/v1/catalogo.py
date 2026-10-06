from dataclasses import asdict

from fastapi import APIRouter

from app.core.categorias import CATEGORIAS, ZONAS
from app.schemas import CatalogoRead

router = APIRouter(tags=["catalogo"])


@router.get("/catalogo", response_model=CatalogoRead)
def catalogo():
    return CatalogoRead(zonas=[asdict(z) for z in ZONAS], categorias=[asdict(c) for c in CATEGORIAS])
