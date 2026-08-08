"""Utilidades compartidas para los tests (factorys y helpers)."""
from django.contrib.auth import get_user_model

from compra.models import (
    Supermercado, Pasillo, Keyword,
    Categoria, CategoriaKeyword, Lista, ListaItem,
)

PASSWORD = 'clave12345'


def crear_usuario(username='usuario', email=None, password=PASSWORD, **kwargs):
    if email is None:
        email = f'{username}@test.com'
    return get_user_model().objects.create_user(
        username=username, email=email, password=password, **kwargs
    )


def crear_superusuario(username='admin', email=None, password=PASSWORD, **kwargs):
    if email is None:
        email = f'{username}@test.com'
    return get_user_model().objects.create_superuser(
        username=username, email=email, password=password, **kwargs
    )


def crear_supermercado(usuario, nombre='Mi Super', **kwargs):
    return Supermercado.objects.create(usuario=usuario, nombre=nombre, **kwargs)


def crear_pasillo(supermercado, nombre='Pasillo', orden=None, categorias=None):
    if orden is None:
        orden = supermercado.pasillos.count() + 1
    pasillo = Pasillo.objects.create(
        supermercado=supermercado, nombre=nombre, orden=orden
    )
    if categorias:
        pasillo.categorias.set(categorias)
    return pasillo


def crear_keyword(pasillo, palabra):
    return Keyword.objects.create(pasillo=pasillo, palabra=palabra)


def crear_categoria(nombre='Panadería', palabras=None):
    categoria = Categoria.objects.create(nombre=nombre)
    for palabra in (palabras or []):
        CategoriaKeyword.objects.create(categoria=categoria, palabra=palabra)
    return categoria


def crear_lista(usuario, supermercado, activa=True, es_plantilla=False, nombre_plantilla=''):
    return Lista.objects.create(
        usuario=usuario,
        supermercado=supermercado,
        activa=activa,
        es_plantilla=es_plantilla,
        nombre_plantilla=nombre_plantilla,
    )


def crear_item(lista, nombre, pasillo=None, en_carro=False):
    return ListaItem.objects.create(
        lista=lista, nombre=nombre, pasillo=pasillo, en_carro=en_carro
    )


def login(client, usuario, password=PASSWORD):
    """Login con email (USERNAME_FIELD del modelo Usuario)."""
    return client.login(username=usuario.email, password=password)
