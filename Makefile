.PHONY: sync test lint typecheck build verify verify-reference verify-independent audit

sync:
	uv sync --all-groups

test:
	uv run pytest

lint:
	uv run ruff check .

typecheck:
	uv run mypy

build:
	uv build

verify: verify-reference verify-independent

verify-reference:
	uv run minoverlap verify-baseline

verify-independent:
	uv run minoverlap verify-independent

audit:
	uv run minoverlap audit
