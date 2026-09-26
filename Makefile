.DEFAULT_GOAL := help
.PHONY: help run jarvis lint format typecheck imports test check vault clean

help:  ## ro'yxat
	@grep -hE '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed -E 's/:[^#]*## /\t/' | expand -t 14

run:  ## development server, faqat localhost
	uv run uvicorn app.main:app --reload --host 127.0.0.1 --port $${JARVIS_PORT:-8765}

jarvis:  ## JARVIS oynasi (backend'ni o'zi ishga tushiradi)
	uv run python -m desktop

lint:  ## ruff tekshiruvi
	uv run ruff check app tests scripts desktop

format:  ## kodni formatlash
	uv run ruff format app tests scripts desktop

typecheck:  ## mypy
	uv run mypy app desktop

imports:  ## qatlam qoidalari
	uv run lint-imports

test:  ## testlar
	uv run pytest

vault:  ## vault papkasini yaratish va vault_template'dan to'ldirish
	uv run python -m scripts.init_vault

clean:  ## __pycache__ tozalash
	@find . -path ./.venv -prune -o -name __pycache__ -type d -print0 | xargs -0 rm -rf

check:  ## ish tugashidan oldin hammasi o'tishi shart
	uv run ruff check app tests scripts desktop
	uv run ruff format --check app tests scripts desktop
	uv run mypy app desktop
	uv run lint-imports
	uv run pytest -q
