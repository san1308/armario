FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dependencias primero (capa cacheable)
COPY pyproject.toml ./
RUN mkdir app && touch app/__init__.py && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir . && \
    rm -rf app

# Modelo de recorte descargado en la imagen (~170 MB): así el primer uso no
# espera a la descarga y el contenedor no necesita salir a internet.
ENV U2NET_HOME=/models
RUN python -c "from rembg import new_session; new_session('isnet-general-use')"

COPY . .
RUN mkdir -p /app/data

EXPOSE 8006

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8006/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8006", "--proxy-headers", "--forwarded-allow-ips", "*"]
