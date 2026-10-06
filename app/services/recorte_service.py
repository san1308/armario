"""Procesado de imágenes: quitar el fondo (rembg) y el gancho de la percha.

Pensado para fotos de prendas colgadas en percha sobre pared clara. Probado
con las fotos reales: el modelo `isnet-general-use` da mejores bordes que
`u2net` en prendas blancas sobre pared blanca; `birefnet` es mejor aún pero
no cabe en memoria en una Raspberry Pi.

Flujo:
    original ──rembg──▶ sinfondo (RGBA, mismo tamaño que la foto)
    sinfondo ──limpieza + corte superior + recorte al contenido──▶ recorte
"""
from __future__ import annotations

import io
import threading
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageOps

from app.core.config import settings

try:  # permite subir HEIC desde iPhone/iPad
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:  # pragma: no cover
    pass

LADO_MAX = 1600          # tamaño máximo con el que se guarda el original
LADO_RECORTE = 1200      # tamaño máximo del recorte final
LADO_MINI = 360

_session = None
_lock = threading.Lock()


def _sesion():
    global _session
    with _lock:
        if _session is None:
            from rembg import new_session  # import perezoso: tarda en cargar

            _session = new_session(settings.modelo_recorte)
    return _session


def abrir_normalizada(data: bytes) -> Image.Image:
    """Abre JPEG/PNG/HEIC, aplica la rotación EXIF y limita el tamaño."""
    im = Image.open(io.BytesIO(data))
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((LADO_MAX, LADO_MAX))
    return im


def quitar_fondo(original: Image.Image) -> Image.Image:
    """Devuelve RGBA del mismo tamaño que `original` con el fondo transparente."""
    from rembg import remove

    return remove(original, session=_sesion(), post_process_mask=True).convert("RGBA")


@dataclass
class Resultado:
    imagen: Image.Image      # RGBA recortada al contenido
    corte_auto: float        # fila (0-1) donde el algoritmo situó el corte superior


def _ancho_fila(fila: np.ndarray) -> int:
    xs = np.flatnonzero(fila)
    return int(xs[-1] - xs[0] + 1) if len(xs) else 0


def calcular_corte_gancho(alfa: np.ndarray) -> int:
    """Fila donde empieza la prenda, por debajo del gancho de la percha.

    Recorre desde arriba y busca la primera fila cuyo ancho opaco supera el
    12 % del ancho típico de la prenda (medido en su tercio central). Lo que
    queda por encima es estrecho: el gancho de la percha o las pinzas.
    """
    opaco = alfa > 128
    filas = np.flatnonzero(opaco.any(axis=1))
    if len(filas) == 0:
        return 0
    anchos = np.array([_ancho_fila(opaco[y]) for y in range(alfa.shape[0])])
    alto = filas[-1] - filas[0]
    cuerpo = anchos[filas[0] + alto // 3: filas[-1] - alto // 3 + 1]
    ref = np.median(cuerpo[cuerpo > 0]) if (cuerpo > 0).any() else anchos.max()
    umbral = 0.12 * ref
    for y in filas:
        siguiente = anchos[min(y + 3, len(anchos) - 1)]
        if anchos[y] >= umbral and siguiente >= umbral:
            return int(y)
    return int(filas[0])


def _quitar_manchas(alfa: np.ndarray) -> np.ndarray:
    """Conserva solo componentes grandes (≥3 % del mayor): quita restos de pared."""
    import cv2

    binaria = (alfa > 64).astype(np.uint8)
    n, etiquetas, stats, _ = cv2.connectedComponentsWithStats(binaria, connectivity=8)
    if n <= 2:
        return alfa
    areas = stats[1:, cv2.CC_STAT_AREA]
    mantener = np.zeros(n, dtype=bool)
    mantener[1:] = areas >= 0.03 * areas.max()
    return np.where(mantener[etiquetas], alfa, 0).astype(np.uint8)


def recortar(sinfondo: Image.Image, corte_manual: float | None = None) -> Resultado:
    """Limpia, aplica el corte superior y recorta al contenido."""
    arr = np.array(sinfondo.convert("RGBA"))
    alfa = _quitar_manchas(arr[:, :, 3])
    corte_auto = calcular_corte_gancho(alfa)
    corte = int(corte_manual * alfa.shape[0]) if corte_manual is not None else corte_auto
    alfa = alfa.copy()
    alfa[:corte] = 0
    arr[:, :, 3] = alfa
    im = Image.fromarray(arr, "RGBA")
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)
    im.thumbnail((LADO_RECORTE, LADO_RECORTE))
    return Resultado(imagen=im, corte_auto=corte_auto / alfa.shape[0])


def miniatura(recorte: Image.Image) -> Image.Image:
    mini = recorte.copy()
    mini.thumbnail((LADO_MINI, LADO_MINI))
    return mini
