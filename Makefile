.PHONY: lint type check run install smoke-e2e

# WeasyPrint's CFFI bindings can't resolve Homebrew dylibs on macOS without a
# hint; harmless on Linux/Render where the libs are in the standard search path.
DYLD := DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib

install:
	pip install -e '.[dev]'

lint:
	ruff check .

type:
	$(DYLD) mypy app scripts

check: lint type

run:
	$(DYLD) uvicorn app.main:app --reload

smoke-e2e:
	$(DYLD) python -m scripts.smoke_e2e $(ARGS)
