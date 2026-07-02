import os
import django
from dotenv import load_dotenv
load_dotenv()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from usuarios.models import FeatureFlag

flags = [
    {
        'nombre': 'plantillas',
        'descripcion': 'Guardar listas como plantillas reutilizables',
        'activo': False,
    },
    {
        'nombre': 'historial',
        'descripcion': 'Ver listas anteriores y recuperarlas',
        'activo': False,
    },
    {
        'nombre': 'productos_favoritos',
        'descripcion': 'Marcar productos como favoritos para añadirlos rápido',
        'activo': False,
    },
    {
        'nombre': 'sugerencias_inteligentes',
        'descripcion': 'Sugerencias basadas en el historial de compras',
        'activo': False,
        'solo_superusuarios': True,
    },
    {
        'nombre': 'compartir_lista',
        'descripcion': 'Generar enlace para compartir la lista',
        'activo': False,
    },
    {
        'nombre': 'exportar_pdf',
        'descripcion': 'Descargar la lista como PDF',
        'activo': False,
    },
    {
        'nombre': 'estadisticas',
        'descripcion': 'Ver estadísticas personales de compra',
        'activo': False,
    },
    {
        'nombre': 'modo_colaborativo',
        'descripcion': 'Compartir lista editable con otra persona',
        'activo': False,
        'solo_superusuarios': True,
    },
    {
        'nombre': 'onboarding',
        'descripcion': 'Guía de bienvenida para usuarios nuevos',
        'activo': True,
    },
    {
        'nombre': 'configuracion_super',
        'descripcion': 'Vista para que el usuario configure su supermercado',
        'activo': True,
    },
]

creados = 0
for f in flags:
    _, creado = FeatureFlag.objects.get_or_create(
        nombre=f['nombre'],
        defaults={
            'descripcion': f['descripcion'],
            'activo': f.get('activo', False),
            'solo_superusuarios': f.get('solo_superusuarios', False),
        }
    )
    estado = '✅ creado' if creado else 'ℹ️  ya existía'
    print(f"  {estado}: {f['nombre']}")
    if creado:
        creados += 1

print(f"\n🎉 {creados} flags nuevos creados, {len(flags) - creados} ya existían")