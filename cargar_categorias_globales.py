"""
Siembra las categorías globales (independientes de cualquier supermercado)
a partir del catálogo genérico ya escrito en cargar_datos.py. Un pasillo de
CUALQUIER supermercado puede etiquetarse con estas categorías para heredar
de golpe sus palabras clave, en vez de tener que escribirlas una a una.

Uso (una sola vez, es idempotente):
    python cargar_categorias_globales.py
"""
import ast
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from compra.models import Categoria, CategoriaKeyword


def _extraer_datos_de_cargar_datos():
    ruta = os.path.join(os.path.dirname(__file__), 'cargar_datos.py')
    src = open(ruta, encoding='utf-8').read()
    inicio = src.index('datos = [')
    fin = src.index('\n\n    total_keywords')
    literal = src[inicio + len('datos = '):fin + 1]
    # datos = [(nombre, orden, [keywords]), ...]
    return ast.literal_eval(literal)


def cargar_categorias_globales():
    datos = _extraer_datos_de_cargar_datos()

    total_creadas = 0
    total_keywords = 0
    for nombre, _orden, palabras in datos:
        categoria, creada = Categoria.objects.get_or_create(nombre=nombre)
        if creada:
            total_creadas += 1

        kws = [CategoriaKeyword(categoria=categoria, palabra=p) for p in palabras]
        CategoriaKeyword.objects.bulk_create(kws, ignore_conflicts=True)
        total_keywords += len(palabras)
        print(f"  ✅ {nombre} ({len(palabras)} keywords)")

    print(f"\n🎉 Carga completada:")
    print(f"   → {len(datos)} categorías procesadas ({total_creadas} nuevas)")
    print(f"   → {total_keywords} palabras clave procesadas")


if __name__ == '__main__':
    cargar_categorias_globales()
