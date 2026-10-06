import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.types import Scope

from app.api.v1 import router as v1_router
from app.core.config import settings
from app.core.lifespan import lifespan

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Alembic reconfigura el logging raíz a WARN al migrar; los logs de la app siguen en INFO
logging.getLogger("app").setLevel(logging.DEBUG if settings.debug else logging.INFO)

app = FastAPI(title="Armario", version="0.1.0", lifespan=lifespan)

app.include_router(v1_router, prefix="/api/v1")


class NoCacheStaticFiles(StaticFiles):
    """Obliga al navegador a revalidar: tras un despliegue el móvil coge la versión nueva.
    Con ETag, si no ha cambiado, la respuesta es un 304 ligero."""

    async def get_response(self, path: str, scope: Scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


# El front (SPA) se sirve en la raíz; se monta el último para no tapar /api
app.mount("/", NoCacheStaticFiles(directory="front", html=True), name="front")
