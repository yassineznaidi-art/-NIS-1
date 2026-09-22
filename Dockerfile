# NIS App v0.1 — Production Dockerfile (no NIS Core redesign)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TMPDIR=/tmp

WORKDIR /app

# System deps for torch / sklearn
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer cache
COPY requirements_v03.txt requirements_app.txt ./
RUN mkdir -p /tmp && TMPDIR=/tmp pip install --no-cache-dir -r requirements_v03.txt && \
    pip install --no-cache-dir -r requirements_app.txt

# Copy app
COPY . .

# Ensure data dirs exist
RUN mkdir -p data/memory logs && \
    python setup_memory.py || true

EXPOSE 8000

# Env defaults (override in host)
ENV MODEL_PROVIDER=nis_core \
    NIS_USE_DENSE=false \
    NIS_DEBUG=false \
    HOST=0.0.0.0 \
    PORT=8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/health', timeout=5).getcode()==200 else 1)"

CMD ["sh","-c","uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
