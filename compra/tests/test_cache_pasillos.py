"""Tests de la caché de candidatos de pasillos (compra.cache_pasillos) y de
su invalidación automática vía signals al cambiar keywords, pasillos o
keywords de categorías globales."""
from django.core.cache import cache
from django.test import TestCase

from compra.cache_pasillos import (
    clave_candidatos,
    invalidar_candidatos,
    invalidar_candidatos_global,
)
from compra.models import CategoriaKeyword
from compra.tests.utils import (
    crear_categoria,
    crear_keyword,
    crear_pasillo,
    crear_supermercado,
    crear_usuario,
)
from compra.views import _candidatos, inferir_pasillo


class CandidatosCacheTests(TestCase):

    def setUp(self):
        cache.clear()
        self.usuario = crear_usuario()

    def test_candidatos_se_cachean_por_supermercado(self):
        supermercado = crear_supermercado(self.usuario)
        pasillo = crear_pasillo(supermercado, nombre='Conservas')
        crear_keyword(pasillo, 'atun')
        cache.delete(clave_candidatos(supermercado))

        _candidatos(supermercado)

        candidatos = cache.get(clave_candidatos(supermercado))
        self.assertIsNotNone(candidatos)
        self.assertIn(('atun', pasillo.id), candidatos)

    def test_invalidar_candidatos_borra_la_clave(self):
        supermercado = crear_supermercado(self.usuario)
        crear_pasillo(supermercado, nombre='Conservas')
        _candidatos(supermercado)
        clave = clave_candidatos(supermercado)
        self.assertIsNotNone(cache.get(clave))

        invalidar_candidatos(supermercado)

        self.assertIsNone(cache.get(clave))

    def test_invalidar_candidatos_global_cambia_la_clave(self):
        supermercado = crear_supermercado(self.usuario)
        clave_antes = clave_candidatos(supermercado)

        invalidar_candidatos_global()

        self.assertNotEqual(clave_antes, clave_candidatos(supermercado))

    def test_invalidacion_al_crear_keyword(self):
        supermercado = crear_supermercado(self.usuario)
        pasillo = crear_pasillo(supermercado, nombre='Conservas')
        self.assertIsNone(inferir_pasillo('atun', supermercado))

        crear_keyword(pasillo, 'atun')

        self.assertEqual(inferir_pasillo('atun', supermercado), pasillo)

    def test_invalidacion_al_modificar_keyword(self):
        supermercado = crear_supermercado(self.usuario)
        pasillo = crear_pasillo(supermercado, nombre='Conservas')
        crear_keyword(pasillo, 'atun')
        self.assertEqual(inferir_pasillo('atun', supermercado), pasillo)

        kw = pasillo.keywords.get(palabra='atun')
        kw.palabra = 'garbanzos'
        kw.save()

        self.assertIsNone(inferir_pasillo('atun', supermercado))
        self.assertEqual(inferir_pasillo('garbanzos', supermercado), pasillo)

    def test_invalidacion_al_eliminar_keyword(self):
        supermercado = crear_supermercado(self.usuario)
        pasillo = crear_pasillo(supermercado, nombre='Conservas')
        kw = crear_keyword(pasillo, 'atun')
        self.assertEqual(inferir_pasillo('atun', supermercado), pasillo)

        kw.delete()

        self.assertIsNone(inferir_pasillo('atun', supermercado))

    def test_invalidacion_global_al_crear_categoria_keyword(self):
        supermercado = crear_supermercado(self.usuario)
        categoria = crear_categoria(nombre='Panadería')
        pasillo = crear_pasillo(
            supermercado, nombre='Pan', categorias=[categoria]
        )
        self.assertIsNone(inferir_pasillo('pan', supermercado))

        CategoriaKeyword.objects.create(categoria=categoria, palabra='pan')

        self.assertEqual(inferir_pasillo('pan', supermercado), pasillo)
