.PHONY: lint type test check run install smoke-e2e

install:
	pip install -e '.[dev]'

lint:
	ruff check .

type:
	mypy app scripts

test:
	python3 -m pytest

check: lint type test

run:
	uvicorn app.main:app --reload

smoke-e2e:
	python -m scripts.smoke_e2e $(ARGS)
