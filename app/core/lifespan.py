import logging
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI

from app.core.config import settings
from app.services import procesado_service

logger = logging.getLogger(__name__)


def _run_migrations() -> None:
    command.upgrade(Config("alembic.ini"), "head")
    logger.info("Migraciones aplicadas.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.prendas_dir.mkdir(parents=True, exist_ok=True)
    _run_migrations()
    procesado_service.reencolar_pendientes()
    logger.info("Armario iniciado.")
    yield
    procesado_service.apagar()
    logger.info("Armario detenido.")
