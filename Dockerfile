FROM python:3.11-slim

# Metadatos
LABEL maintainer="SAL-9000 <noreply@landsraad.empire>"
LABEL description="🎭 Parody Critics API - Marco Aurelio & Rosario Costras"
LABEL version="1.0.0"

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PARODY_CRITICS_ENV=production \
    PARODY_CRITICS_HOST=0.0.0.0 \
    PARODY_CRITICS_PORT=8000 \
    PARODY_CRITICS_DB_PATH=/app/data/critics.db

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Crear directorio para base de datos (la DB se inicializa en runtime o se monta via volumen)
RUN mkdir -p /app/data

# Crear usuario no-root para seguridad
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Exponer puerto
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Comando por defecto
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]