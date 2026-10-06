"""Importa de golpe una carpeta de fotos al armario de un usuario.

Uso (dentro del contenedor):
    docker compose exec armario python -m scripts.importar \\
        --email mama@example.com --carpeta importar \\
        --clasificacion scripts/clasificacion_inicial.csv

- Ignora lo que no sea imagen (p. ej. los .MOV de las Live Photos).
- Es idempotente: si una foto con el mismo nombre ya está en el armario, la salta.
- Procesa las fotos una a una en primer plano (en la Pi, ~5-10 s cada una).
- El CSV opcional (foto,categoria,temporadas) asigna categoría y temporadas
  iniciales (temporadas separadas por "|"); se corrigen luego desde la app.
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlmodel import Session, select

from app.core.auth import obtener_o_crear_usuario
from app.core.categorias import POR_SLUG, TEMPORADA_SLUGS
from app.core.config import settings
from app.core.database import engine
from app.models import Prenda
from app.services import prenda_service

EXTENSIONES = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp"}


def leer_clasificacion(ruta: Path | None) -> dict[str, tuple[str | None, list[str]]]:
    """CSV → {"IMG_0133": ("blusa", ["verano", "entretiempo"]), ...}"""
    if ruta is None:
        return {}
    mapa = {}
    with ruta.open(encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            foto = fila["foto"].strip()
            cat = (fila.get("categoria") or "").strip() or None
            temps = [t.strip() for t in (fila.get("temporadas") or "").split("|") if t.strip()]
            if cat and cat not in POR_SLUG:
                sys.exit(f"Categoría desconocida en el CSV: {cat} ({foto})")
            if any(t not in TEMPORADA_SLUGS for t in temps):
                sys.exit(f"Temporada desconocida en el CSV: {temps} ({foto})")
            mapa[foto.upper()] = (cat, temps)
    return mapa


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--email", required=True, help="Usuario dueño de las prendas")
    ap.add_argument("--carpeta", required=True, type=Path)
    ap.add_argument("--clasificacion", type=Path, help="CSV con columnas foto,categoria,temporadas")
    args = ap.parse_args()

    settings.procesar_en_segundo_plano = False   # procesar aquí mismo, una a una
    settings.prendas_dir.mkdir(parents=True, exist_ok=True)
    command.upgrade(Config("alembic.ini"), "head")

    clasificacion = leer_clasificacion(args.clasificacion)
    fotos = sorted(p for p in args.carpeta.iterdir() if p.suffix.lower() in EXTENSIONES)
    print(f"{len(fotos)} fotos en {args.carpeta}")

    with Session(engine) as session:
        usuario = obtener_o_crear_usuario(session, args.email.strip().lower())
        ya = set(session.exec(select(Prenda.nombre_archivo).where(Prenda.usuario_id == usuario.id)).all())
        hechas = saltadas = errores = 0
        t0 = time.time()
        for i, foto in enumerate(fotos, 1):
            if foto.name in ya:
                saltadas += 1
                continue
            categoria, temporadas = clasificacion.get(foto.stem.upper(), (None, []))
            try:
                p = prenda_service.crear_desde_foto(session, usuario, foto.read_bytes(), foto.name,
                                                    categoria, temporadas)
                session.refresh(p)
                hechas += 1
                print(f"[{i}/{len(fotos)}] {foto.name} → {categoria or 'sin clasificar'} ({p.estado.value})")
            except ValueError as e:
                errores += 1
                print(f"[{i}/{len(fotos)}] {foto.name}: {e}")
        print(f"Importadas {hechas}, ya existían {saltadas}, errores {errores} — {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
