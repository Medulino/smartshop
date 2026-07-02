FROM python:3.13-slim

# Variables de entorno para Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

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
# Puerto
EXPOSE 8000

# Arrancar con gunicorn (servidor de producción)
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]