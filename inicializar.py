import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
Usuario = get_user_model()

if not Usuario.objects.filter(is_superuser=True).exists():
    password = os.getenv('ADMIN_PASSWORD')
    if not password:
        raise SystemExit(
            'ERROR: ADMIN_PASSWORD no está definido. '
            'Fija un password fuerte para el superusuario antes de arrancar.'
        )
    Usuario.objects.create_superuser(
        username=os.getenv('ADMIN_USERNAME', 'admin'),
        email=os.getenv('ADMIN_EMAIL', 'admin@smartshop.com'),
        password=password
    )
    print("✅ Superusuario creado")
else:
    print("ℹ️ Superusuario ya existe")
