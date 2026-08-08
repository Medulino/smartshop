FROM python:3.13-slim

# Variables de entorno para Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOME=/app

# Directorio de trabajo
WORKDIR /app

# Dependencias del sistema necesarias para WeasyPrint y psycopg2
RUN apt-get update && apt-get install -y \
    gcc \
    python3-cffi \
    python3-brotli \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libffi-dev \
    libjpeg-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el proyecto
COPY . .

# Recopilar archivos estáticos
RUN SECRET_KEY=build-temp-key-not-used-in-production \
    ALLOWED_HOSTS=localhost \
    DB_NAME=dummy DB_USER=dummy DB_PASSWORD=dummy \
    python manage.py collectstatic --noinput

# Usuario sin privilegios para ejecutar gunicorn (el contenedor nunca corre
# como root: un escape de contenedor no debe dar root en el host)
RUN useradd --system --uid 1001 appuser \
    && chown -R appuser:appuser /app

USER appuser

# Puerto
EXPOSE 8000

# Arrancar con gunicorn. Timeouts para no dejar colgados los workers con
# peticiones lentas (IA/PDF) y reciclaje de memoria por cada 1000 peticiones.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "--graceful-timeout", "60", "--keep-alive", "5", "--max-requests", "1000", "--max-requests-jitter", "100"]