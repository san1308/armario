.PHONY: setup install run test build up down logs migrate importar temporadas

setup:
	python3.12 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[dev]"

install:
	.venv/bin/pip install -e ".[dev]"

run:
	DEV_EMAIL=$${DEV_EMAIL:-yo@local} .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8006 --reload

test:
	.venv/bin/python -m pytest tests/ -v

migrate:
	.venv/bin/alembic upgrade head

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f armario

# make importar EMAIL=mama@ejemplo.com
importar:
	docker compose exec armario python -m scripts.importar --email $(EMAIL) --carpeta importar --clasificacion scripts/clasificacion_inicial.csv

# Para armarios importados antes de las temporadas: make temporadas EMAIL=mama@ejemplo.com
temporadas:
	docker compose exec armario python -m scripts.aplicar_temporadas --email $(EMAIL) --clasificacion scripts/clasificacion_inicial.csv
