"""Aplica las temporadas del CSV a prendas que ya están en el armario.

Para quien importó antes de que existieran las temporadas. Empareja por el
nombre de la foto (IMG_0133.JPEG ↔ IMG_0133 en el CSV).

Uso (dentro del contenedor):
    docker compose exec armario python -m scripts.aplicar_temporadas \\
        --email mama@example.com --clasificacion scripts/clasificacion_inicial.csv

Por defecto solo rellena las prendas que aún no tienen temporada, para no
pisar lo que se haya cambiado a mano desde la app. --forzar las sobrescribe.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlmodel import Session, select

from app.core.categorias import normalizar_temporadas
from app.core.database import engine
from app.models import Prenda, Usuario
from scripts.importar import leer_clasificacion


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--email", required=True)
    ap.add_argument("--clasificacion", required=True, type=Path)
    ap.add_argument("--forzar", action="store_true", help="Sobrescribir también las que ya tienen temporada")
    args = ap.parse_args()

    command.upgrade(Config("alembic.ini"), "head")
    clasificacion = leer_clasificacion(args.clasificacion)

    with Session(engine) as session:
        usuario = session.exec(select(Usuario).where(Usuario.email == args.email.strip().lower())).first()
        if usuario is None:
            raise SystemExit(f"No existe el usuario {args.email}")
        prendas = session.exec(select(Prenda).where(Prenda.usuario_id == usuario.id)).all()
        cambiadas = saltadas = sin_dato = 0
        for p in prendas:
            stem = Path(p.nombre_archivo or "").stem.upper()
            if stem not in clasificacion or not clasificacion[stem][1]:
                sin_dato += 1
                continue
            if p.temporadas and not args.forzar:
                saltadas += 1
                continue
            p.temporadas = normalizar_temporadas(clasificacion[stem][1])
            session.add(p)
            cambiadas += 1
        session.commit()
    print(f"Actualizadas {cambiadas}, ya tenían temporada {saltadas}, sin dato en el CSV {sin_dato}")


if __name__ == "__main__":
    main()
