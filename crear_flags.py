import os
import django
from dotenv import load_dotenv
load_dotenv()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from usuarios.models import FeatureFlag

# Plan premium: los flags con requiere_premium=True solo los usan los
# usuarios premium. El superusuario NO tiene ventajas: también se le aplica
# su plan. Lo que antes era 'solo_superusuarios' pasa a ser 'requiere_premium'.
flags = [
    {
        'nombre': 'plantillas',
        'descripcion': 'Guardar listas como plantillas reutilizables',
        'activo': False,
        'requiere_premium': True,
    },
    {
        'nombre': 'historial',
        'descripcion': 'Ver listas anteriores y recuperarlas',
        'activo': False,
        'requiere_premium': True,
    },
    {
        'nombre': 'productos_favoritos',
        'descripcion': 'Marcar productos como favoritos para añadirlos rápido',
        'activo': False,
        'requiere_premium': True,
    },
    {
        'nombre': 'sugerencias_inteligentes',
        'descripcion': 'Sugerencias basadas en el historial de compras',
        'activo': False,
        'requiere_premium': True,
    },
    {
        'nombre': 'compartir_lista',
        'descripcion': 'Generar enlace para compartir la lista',
        'activo': False,
        'requiere_premium': True,
    },
    {
        'nombre': 'exportar_pdf',
        'descripcion': 'Descargar la lista como PDF',
        'activo': False,
        'requiere_premium': True,
    },
    {
        'nombre': 'estadisticas',
        'descripcion': 'Ver estadísticas personales de compra',
        'activo': False,
        'requiere_premium': True,
    },
    {
        'nombre': 'modo_colaborativo',
        'descripcion': 'Compartir lista editable con otra persona',
        'activo': False,
        'requiere_premium': True,
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
    {
        'nombre': 'supermercados_publicos',
        'descripcion': 'Publicar supermercados propios y usar los de otros usuarios (con likes)',
        'activo': True,
    },
]

creados = 0
for f in flags:
    flag, creado = FeatureFlag.objects.get_or_create(
        nombre=f['nombre'],
        defaults={
            'descripcion': f['descripcion'],
            'activo': f.get('activo', False),
            'requiere_premium': f.get('requiere_premium', False),
        }
    )
    # En flags ya existentes, mantener la configuración de plan actualizada
    # por si cambió el diseño (por ejemplo: solo_superusuarios -> premium).
    if not creado and flag.requiere_premium != f.get('requiere_premium', False):
        flag.requiere_premium = f.get('requiere_premium', False)
        flag.save(update_fields=['requiere_premium'])
        print(f"  🔁 actualizado a premium: {f['nombre']}")
    estado = '✅ creado' if creado else 'ℹ️  ya existía'
    print(f"  {estado}: {f['nombre']}")
    if creado:
        creados += 1

print(f"\n🎉 {creados} flags nuevos creados, {len(flags) - creados} ya existían")
