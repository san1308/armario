from dataclasses import asdict

from fastapi import APIRouter

from app.core.categorias import CATEGORIAS, TEMPORADAS, ZONAS
from app.schemas import CatalogoRead

router = APIRouter(tags=["catalogo"])


@router.get("/catalogo", response_model=CatalogoRead)
def catalogo():
    return CatalogoRead(zonas=[asdict(z) for z in ZONAS], categorias=[asdict(c) for c in CATEGORIAS],
                        temporadas=[asdict(t) for t in TEMPORADAS])
