import os
import shutil
import tempfile

# Debe ejecutarse antes de cualquier import de la app para que pydantic-settings
# lea la configuración de pruebas y no el .env
_TMP = tempfile.mkdtemp(prefix="armario-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["DATA_DIR"] = _TMP
os.environ["PROCESAR_EN_SEGUNDO_PLANO"] = "false"
os.environ["DEV_EMAIL"] = ""
os.environ["EMAILS_PERMITIDOS"] = ""

import io  # noqa: E402

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from sqlalchemy import text  # noqa: E402

MAMA = {"Cf-Access-Authenticated-User-Email": "mama@example.com"}
OTRA = {"Cf-Access-Authenticated-User-Email": "otra@example.com"}


def quitar_fondo_falso(original: Image.Image) -> Image.Image:
    """Sustituye a rembg en los tests: todo lo que no es casi blanco es prenda."""
    arr = np.array(original.convert("RGB")).astype(int)
    alfa = np.where(arr.min(axis=2) < 200, 255, 0).astype(np.uint8)
    rgba = original.convert("RGBA")
    rgba.putalpha(Image.fromarray(alfa))
    return rgba


def foto_prenda(color=(200, 30, 60), con_gancho=True) -> bytes:
    """Foto sintética: pared blanca, 'camiseta' rectangular y gancho fino encima."""
    im = Image.new("RGB", (600, 800), (245, 245, 240))
    d = ImageDraw.Draw(im)
    d.rectangle([150, 200, 450, 700], fill=color)
    if con_gancho:
        d.rectangle([295, 100, 305, 200], fill=(40, 40, 40))
    buf = io.BytesIO()
    im.save(buf, "JPEG")
    return buf.getvalue()


@pytest.fixture(scope="session", autouse=True)
def _parchear_rembg():
    from app.services import recorte_service

    original = recorte_service.quitar_fondo
    recorte_service.quitar_fondo = quitar_fondo_falso
    yield
    recorte_service.quitar_fondo = original
    shutil.rmtree(_TMP, ignore_errors=True)


@pytest.fixture(scope="session")
def client():
    from app.main import app

    with TestClient(app) as c:  # el lifespan aplica las migraciones
        yield c


@pytest.fixture(autouse=True)
def limpiar_bd(client):
    yield
    from app.core.database import engine

    with engine.connect() as conn:
        for tabla in ("conjunto", "prenda", "usuario"):
            conn.execute(text(f"DELETE FROM {tabla}"))
        conn.commit()
