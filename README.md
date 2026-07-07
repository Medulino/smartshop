# 🛒 Compra Inteligente

🌐 **Demo en producción:** https://smartshop-jc36.onrender.com

Aplicación web desarrollada como proyecto final de curso. 
Permite gestionar listas de la compra de forma inteligente, ordenando los productos según los pasillos del supermercado del usuario y leyendo listas manuscritas mediante IA para una ruta optimizada ahorrando tiempo
para el usuario.

Es un proyecto totalmente modulable. Está orientado a la compra de supermercado pero se puede configurar para 
cualquer tipo de establecimiento.

## Tecnologías

- Python 3.13
- Django 6
- PostgreSQL 17
- Bootstrap 5
- Docker + Docker Compose
- Google Gemini API (lectura de fotos con IA)
- WeasyPrint (exportación PDF)
- Pillow (procesamiento de imágenes)

## Lenguajes utilizados

| Lenguaje | Uso aproximado | Función |
|----------|---------------|---------|
| **Python** | ~75% | Lógica de negocio, modelos de datos, vistas, integración con IA, procesamiento de imágenes, autenticación, backups |
| **HTML** | ~20% | Estructura y presentación de todas las pantallas de la app |
| **JavaScript** | ~5% | Estrictamente lo necesario: spinner de carga, mensajes de estado sin recargar página, y llamadas AJAX a la API |
| **SQL** | Implícito | Gestionado automáticamente por el ORM de Django sobre PostgreSQL |
| **Bash** | Implícito | Scripts de Docker, backups automáticos y arranque de contenedores |


## Funcionalidades

- Registro y login de usuarios
- Asignación automática de productos a pasillos por palabras clave
- Lectura de listas manuscritas mediante IA (foto)
- Redimensionado automático de imágenes antes de procesarlas
- Configuración personalizada de pasillos por supermercado
- Historial de compras y plantillas reutilizables
- Exportación a PDF ordenada por pasillos
- Sistema de feature flags para activar/desactivar funcionalidades
- Preferencias de usuario
- Panel de administración con Jazzmin
- Backups automáticos de PostgreSQL

## Instalación

### Requisitos previos

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### Pasos

**1.** Clona el repositorio:

```bash
git clone URL_DEL_REPOSITORIO
cd compra_inteligente_django
```

**2.** Crea el archivo `.env` usando `.env.example` como referencia:

```bash
cp .env.example .env
```

Edita `.env` con tus valores reales (SECRET_KEY, contraseña de base de datos y API key de Gemini).

**3.** Construye y arranca:

```bash
docker compose up -d
```

**4.** Todo se configura automáticamente al arrancar: 
migraciones, superusuario, datos iniciales y feature flags.
```

**5.** Accede a la aplicación en `http://localhost:8000`

## Gestión de contenedores

```bash
# Ver estado
docker compose ps

# Ver logs
docker compose logs -f

# Parar
docker compose down

# Reconstruir tras cambios
docker compose build
docker compose up -d
```

## Backups

Los backups de PostgreSQL se generan automáticamente cada 24 horas en la carpeta `backups/`. Para hacer un backup manual:

```bash
docker exec compra_backup pg_dump -h db -U $DB_USER $DB_NAME > backups/backup_manual.sql
```

Para restaurar un backup:

```bash
docker exec -i compra_db psql -U $DB_USER $DB_NAME < backups/backup_manual.sql
```

## Autor

Medulino — Proyecto Final de Curso