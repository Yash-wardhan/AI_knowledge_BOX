.PHONY: dev start test lint migrate

# `python -m …` instead of the uvicorn/alembic launcher scripts: those hard-code
# the venv's absolute path and break if the project folder is moved.

dev:
	uv run --frozen python -m uvicorn backend.main:app --app-dir src --reload --port 8000

start:
	uv run --frozen python -m uvicorn backend.main:app --app-dir src --host 0.0.0.0 --port 8000

migrate:
	uv run --frozen python -m alembic upgrade head

test:
	uv run --frozen python -m pytest

lint:
	uv run --frozen ruff check .
