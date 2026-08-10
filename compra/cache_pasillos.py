"""Caché de los candidatos de pasillos (palabras clave) por supermercado.

Vivió dentro de compra.views; se extrajo a un módulo propio para que los
signals de compra.models puedan invalidarla sin importar las vistas.
"""

from django.core.cache import cache

CANDIDATOS_TTL = 300
_GLOBAL_VERSION_KEY = 'candidatos_version_global'


def _version_global():
    """Versión global que se incrementa cuando cambian palabras clave de
    categorías globales (afectan a todos los supermercados que las heredan)."""
    version = cache.get(_GLOBAL_VERSION_KEY)
    if version is None:
        version = 1
        cache.set(_GLOBAL_VERSION_KEY, version, CANDIDATOS_TTL)
    return version


def clave_candidatos(supermercado):
    return f'candidatos_{_version_global()}_{supermercado.id}'


def invalidar_candidatos(supermercado):
    cache.delete(f'candidatos_{_version_global()}_{supermercado.id}')


def invalidar_candidatos_global():
    version = cache.get(_GLOBAL_VERSION_KEY) or 1
    cache.set(_GLOBAL_VERSION_KEY, version + 1, CANDIDATOS_TTL)
