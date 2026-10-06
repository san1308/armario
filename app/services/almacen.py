"""Rutas en disco de los ficheros de cada prenda.

data/prendas/<usuario_id>/<prenda_id>/
    original.jpg   foto subida (rotación EXIF aplicada, máx. 1600 px)
    sinfondo.png   salida de rembg a tamaño completo (base para recortes manuales)
    recorte.webp   prenda final recortada con transparencia (lo que pinta el probador)
    mini.webp      miniatura del recorte para listas
"""
import shutil
from pathlib import Path

from app.core.config import settings
from app.models import Prenda

TIPOS = ("original", "sinfondo", "recorte", "mini")
_EXT = {"original": "jpg", "sinfondo": "png", "recorte": "webp", "mini": "webp"}
MEDIA = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


def carpeta(prenda: Prenda) -> Path:
    return settings.prendas_dir / str(prenda.usuario_id) / str(prenda.id)


def ruta(prenda: Prenda, tipo: str) -> Path:
    return carpeta(prenda) / f"{tipo}.{_EXT[tipo]}"


def media_type(tipo: str) -> str:
    return MEDIA[_EXT[tipo]]


def borrar(prenda: Prenda) -> None:
    shutil.rmtree(carpeta(prenda), ignore_errors=True)
