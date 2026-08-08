"""Tests de los límites de uso (usuario_supero_limite y analizar_foto)."""
from unittest.mock import patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from compra.tests.utils import crear_lista, crear_supermercado, crear_usuario
from compra.views import usuario_supero_limite


class UsuarioSuperoLimiteTests(TestCase):
    def setUp(self):
        cache.clear()
        self.usuario = crear_usuario()

    def test_false_hasta_el_limite_y_true_a_partir_de_ahi(self):
        resultado = [
            usuario_supero_limite(self.usuario, 'accion', limite=3)
            for _ in range(5)
        ]
        self.assertEqual(resultado, [False, False, False, True, True])

    def test_la_cuenta_es_por_accion(self):
        usuario_supero_limite(self.usuario, 'accion_a', limite=3)
        self.assertFalse(
            usuario_supero_limite(self.usuario, 'accion_b', limite=3)
        )

    def test_la_cuenta_es_por_usuario(self):
        otro = crear_usuario('otro')
        usuario_supero_limite(self.usuario, 'accion', limite=1)
        self.assertFalse(
            usuario_supero_limite(otro, 'accion', limite=1)
        )


class AnalizarFotoLimiteTests(TestCase):
    def setUp(self):
        cache.clear()
        self.usuario = crear_usuario()
        self.supermercado = crear_supermercado(self.usuario)
        self.lista = crear_lista(self.usuario, self.supermercado)

    def _foto(self, contenido=b'foto-falsa'):
        return SimpleUploadedFile('lista.jpg', contenido, content_type='image/jpeg')

    @patch('compra.services.leer_lista_desde_imagen')
    def test_429_a_la_undecima_foto(self, mock_ia):
        mock_ia.return_value = (['leche'], None)
        self.client.force_login(self.usuario)
        url = reverse('compra:analizar_foto')

        for _ in range(10):
            respuesta = self.client.post(
                url, {'lista_id': self.lista.id, 'foto': self._foto()}
            )
            self.assertEqual(respuesta.status_code, 200)

        respuesta = self.client.post(
            url, {'lista_id': self.lista.id, 'foto': self._foto()}
        )
        self.assertEqual(respuesta.status_code, 429)
        self.assertIn('límite de 10 fotos', respuesta.json()['error'])

    @patch('compra.services.leer_lista_desde_imagen')
    def test_segundo_usuario_no_limitado(self, mock_ia):
        mock_ia.return_value = (['leche'], None)
        self.client.force_login(self.usuario)
        url = reverse('compra:analizar_foto')

        for _ in range(10):
            respuesta = self.client.post(
                url, {'lista_id': self.lista.id, 'foto': self._foto()}
            )
            self.assertEqual(respuesta.status_code, 200)

        otro = crear_usuario('otro')
        supermercado_otro = crear_supermercado(otro, nombre='Ajeno')
        lista_otro = crear_lista(otro, supermercado_otro)
        self.client.force_login(otro)
        respuesta = self.client.post(
            url, {'lista_id': lista_otro.id, 'foto': self._foto()}
        )
        self.assertEqual(respuesta.status_code, 200)
