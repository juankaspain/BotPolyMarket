# =====================================
# Dockerfile para BotPolyMarket
# =====================================
# Bot de trading automatizado para Polymarket
# Construido con Python 3.11 y dependencias optimizadas

# Etapa 1: Builder - Construir dependencias
FROM python:3.11-slim AS builder

# Metadatos
LABEL maintainer="juankaspain"
LABEL description="Bot de trading automatizado para Polymarket"
LABEL version="1.0.0"

# Variables de entorno para optimización de Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Crear directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias para compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y instalar dependencias de Python
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --user --no-warn-script-location -r requirements.txt

# Etapa 2: Runtime - Imagen final optimizada
FROM python:3.11-slim

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/root/.local/bin:$PATH" \
    TZ=Europe/Madrid

# Crear usuario no-root para seguridad
RUN groupadd -r botuser && useradd -r -g botuser botuser

# Crear directorios necesarios
WORKDIR /app
RUN mkdir -p /app/logs /app/data && \
    chown -R botuser:botuser /app

# Copiar dependencias de Python desde builder
COPY --from=builder --chown=botuser:botuser /root/.local /root/.local

# Copiar código de la aplicación
COPY --chown=botuser:botuser . .

# Asegurar que los scripts sean ejecutables
RUN chmod +x main.py || true

# Cambiar a usuario no-root
USER botuser

# Healthcheck para monitoreo
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Exponer puerto si se usa dashboard web (opcional)
EXPOSE 8080

# Volumen para persistencia de datos
VOLUME ["/app/logs", "/app/data"]

# Comando por defecto
CMD ["python", "main.py"]

# =====================================
# INSTRUCCIONES DE USO:
# =====================================
# 
# Construir la imagen:
#   docker build -t botpolymarket:latest .
#
# Ejecutar el contenedor:
#   docker run -d \
#     --name botpolymarket \
#     --env-file .env \
#     -v $(pwd)/logs:/app/logs \
#     -v $(pwd)/data:/app/data \
#     botpolymarket:latest
#
# Ver logs:
#   docker logs -f botpolymarket
#
# Detener el contenedor:
#   docker stop botpolymarket
#
# Eliminar el contenedor:
#   docker rm botpolymarket
# =====================================
