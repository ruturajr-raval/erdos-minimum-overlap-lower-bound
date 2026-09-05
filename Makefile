.PHONY: sync test lint typecheck build verify verify-reference verify-independent \
	verify-center-arb verify-center-mpfi audit paper-build paper-bundle

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
	latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error \
		-output-directory=build/paper paper/main.tex

paper-bundle:
	python3 tools/build_arxiv_bundle.py
