.PHONY: fmt lint dev

fmt:
	uv run ruff format src
	uv run ruff check src --fix

lint:
	uv run ruff check src
	uv run ty check src

dev:
	cd src && uv run watchmedo auto-restart --patterns '*.py' --recursive -- python -m bot
