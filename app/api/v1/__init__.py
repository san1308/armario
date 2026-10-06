from fastapi import APIRouter

from app.api import health
from app.api.v1 import catalogo, conjuntos, prendas, yo

router = APIRouter()
router.include_router(health.router)
router.include_router(yo.router)
router.include_router(catalogo.router)
router.include_router(prendas.router)
router.include_router(conjuntos.router)
