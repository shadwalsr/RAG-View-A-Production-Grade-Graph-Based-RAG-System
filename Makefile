.PHONY: run test lint docker-up setup

run:
	poetry run uvicorn src.main:app --reload

test:
	poetry run pytest

lint:
	poetry run ruff check .
	poetry run black --check .

format:
	poetry run ruff check --fix .
	poetry run black .

docker-up:
	docker-compose up -d

health-check:
	poetry run python src/health_check.py

setup:
	poetry install
	poetry run pre-commit install
