# ---------- Stage 1: build the Next.js static export ----------
FROM node:20-bookworm-slim AS frontend
WORKDIR /fe
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
# next.config.js must set: output: 'export'  -> produces ./out
RUN npm run build

# ---------- Stage 2: python runtime (single process) ----------
FROM python:3.12-slim-bookworm AS runtime

# WeasyPrint system libraries (Pango/Cairo/GDK-Pixbuf) + a base font.
RUN apt-get update && apt-get install --no-install-recommends -y \
      libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 \
      libcairo2 libgdk-pixbuf-2.0-0 libffi8 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

COPY pyproject.toml ./
# Stub out app/ so setuptools can resolve package metadata and pip can install
# all declared dependencies. The stub is removed before the real source lands,
# preserving the layer-cache benefit when only app/ code changes.
RUN pip install --upgrade pip && \
    mkdir app && touch app/__init__.py && \
    pip install . && \
    rm -rf app

COPY app/ ./app/
# Place the built frontend where StaticFiles expects it.
COPY --from=frontend /fe/out/ ./app/static/

# Run as non-root.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /srv
USER appuser

# Render injects $PORT.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
