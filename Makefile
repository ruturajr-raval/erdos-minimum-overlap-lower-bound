PYTHON ?= python3
SOURCE_DATE_EPOCH ?= 1788739200

.PHONY: sync test lint typecheck build verify verify-reference verify-independent \
	verify-center-arb verify-center-mpfi audit paper-build paper-bundle \
	paper-release verify-release-assets

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

verify: verify-reference verify-independent verify-center-arb verify-center-mpfi

verify-reference:
	uv run minoverlap verify-baseline

verify-independent:
	uv run minoverlap verify-independent

verify-center-arb:
	uv run minoverlap verify-center certificates/center-038055925.tsv

verify-center-mpfi:
	uv run minoverlap verify-center-mpfi certificates/center-038055925.tsv

audit:
	uv run minoverlap audit

paper-build:
	mkdir -p build/paper
	SOURCE_DATE_EPOCH=$(SOURCE_DATE_EPOCH) \
	latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error \
		-output-directory=build/paper paper/main.tex

paper-bundle:
	$(PYTHON) -m tools.build_arxiv_bundle

paper-release: paper-build
	$(PYTHON) -m tools.build_release_assets

verify-release-assets:
	$(PYTHON) -m tools.build_release_assets --verify-only
