#!/bin/bash
python manage.py migrate
python inicializar.py
python cargar_datos.py
python crear_flags.py
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
