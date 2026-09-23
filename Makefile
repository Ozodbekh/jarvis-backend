.DEFAULT_GOAL := help
.PHONY: help run lint format typecheck imports test check vault clean

help:  ## ro'yxat
	@grep -hE '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed -E 's/:[^#]*## /\t/' | expand -t 14

run:  ## development server, faqat localhost
	uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

lint:  ## ruff tekshiruvi
	uv run ruff check app tests scripts

format:  ## kodni formatlash
	uv run ruff format app tests scripts

typecheck:  ## mypy
	uv run mypy app

imports:  ## qatlam qoidalari
	uv run lint-imports

test:  ## testlar
	uv run pytest

vault:  ## vault papkasini yaratish va vault_template'dan to'ldirish
	uv run python scripts/init_vault.py

clean:  ## __pycache__ tozalash
	@find . -path ./.venv -prune -o -name __pycache__ -type d -print0 | xargs -0 rm -rf

check:  ## ish tugashidan oldin hammasi o'tishi shart
	uv run ruff check app tests scripts
	uv run ruff format --check app tests scripts
	uv run mypy app
	uv run lint-imports
	uv run pytest -q
