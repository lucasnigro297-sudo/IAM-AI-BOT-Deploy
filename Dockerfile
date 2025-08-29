# ==== FastAPI ====
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface

# Paquetes base (agregá otros si tu build lo requiere)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Reqs primero para cachear capas
COPY requirements.txt .
RUN pip install -r requirements.txt

# Código
COPY . .

# Puerto FastAPI
EXPOSE 8000

# Salud (opcional: curl /healthz en compose/fly)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
  CMD curl -fsS http://localhost:8000/healthz || exit 1

# Ejecutar
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
