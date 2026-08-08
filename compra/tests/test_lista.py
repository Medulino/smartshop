"""Tests de las vistas de lista de la compra (compra.views)."""
import json
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from compra.models import Keyword, Lista, ListaItem
from compra.tests.utils import (
    crear_item, crear_keyword, crear_lista, crear_pasillo,
    crear_supermercado, crear_usuario,
)


class ListaCompraViewTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario()

    def test_sin_login_redirige_a_login(self):
        respuesta = self.client.get(reverse('compra:lista'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('login', respuesta.url)

    def test_con_login_crea_lista_activa(self):
        self.client.force_login(self.usuario)
        supermercado = crear_supermercado(self.usuario)
        respuesta = self.client.get(reverse('compra:lista'))
        self.assertEqual(respuesta.status_code, 200)
        lista = Lista.objects.get(
            usuario=self.usuario, supermercado=supermercado, activa=True
        )
        self.assertEqual(respuesta.context['lista'], lista)

    def test_sin_supermercados_renderiza_sin_lista(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.get(reverse('compra:lista'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIsNone(respuesta.context['supermercado'])
        self.assertIsNone(respuesta.context['lista'])

    def test_parametro_supermercado_filtra(self):
        self.client.force_login(self.usuario)
        supermercado_1 = crear_supermercado(self.usuario, nombre='Super A')
        supermercado_2 = crear_supermercado(self.usuario, nombre='Super B')
        respuesta = self.client.get(
            reverse('compra:lista') + f'?supermercado={supermercado_2.id}'
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context['supermercado'], supermercado_2)

    def test_supermercado_de_otro_usuario_devuelve_404(self):
        self.client.force_login(self.usuario)
        otro = crear_usuario('otro')
        ajeno = crear_supermercado(otro, nombre='Ajeno')
        respuesta = self.client.get(
            reverse('compra:lista') + f'?supermercado={ajeno.id}'
        )
        self.assertEqual(respuesta.status_code, 404)


class AñadirProductoTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario()
        self.supermercado = crear_supermercado(self.usuario)
        self.lista = crear_lista(self.usuario, self.supermercado)

    def _post(self, **data):
        return self.client.post(
            reverse('compra:añadir_producto'),
            data=json.dumps(data),
            content_type='application/json',
        )

    def test_crea_item_con_pasillo_inferido(self):
        pasillo = crear_pasillo(self.supermercado, nombre='Lácteos', orden=1)
        crear_keyword(pasillo, 'leche')
        self.client.force_login(self.usuario)
        respuesta = self._post(nombre='leche', lista_id=self.lista.id)
        self.assertEqual(respuesta.status_code, 200)
        item = ListaItem.objects.get(lista=self.lista, nombre='leche')
        self.assertEqual(item.pasillo, pasillo)

    def test_varios_productos_separados_por_comas(self):
        self.client.force_login(self.usuario)
        respuesta = self._post(
            nombre='leche, pan, atún', lista_id=self.lista.id
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(ListaItem.objects.filter(lista=self.lista).count(), 3)
        self.assertEqual(len(respuesta.json()['items']), 3)

    def test_separadores_punto_y_coma_y_saltos_de_linea(self):
        self.client.force_login(self.usuario)
        respuesta = self._post(
            nombre='leche; pan\natún', lista_id=self.lista.id
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(ListaItem.objects.filter(lista=self.lista).count(), 3)

    def test_sin_texto_devuelve_400(self):
        self.client.force_login(self.usuario)
        respuesta = self._post(nombre='', lista_id=self.lista.id)
        self.assertEqual(respuesta.status_code, 400)

    def test_sin_lista_id_devuelve_400(self):
        self.client.force_login(self.usuario)
        respuesta = self._post(nombre='leche')
        self.assertEqual(respuesta.status_code, 400)

    def test_lista_de_otro_usuario_devuelve_404(self):
        self.client.force_login(self.usuario)
        otro = crear_usuario('otro')
        ajeno = crear_lista(otro, crear_supermercado(otro, nombre='Ajeno'))
        respuesta = self._post(nombre='leche', lista_id=ajeno.id)
        self.assertEqual(respuesta.status_code, 404)

    def test_sin_login_redirige(self):
        respuesta = self._post(nombre='leche', lista_id=self.lista.id)
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('login', respuesta.url)


class ToggleEnCarroTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario()
        self.supermercado = crear_supermercado(self.usuario)
        self.lista = crear_lista(self.usuario, self.supermercado)
        self.item = crear_item(self.lista, 'leche')

    def test_marca_y_desmarca(self):
        self.client.force_login(self.usuario)
        url = reverse('compra:toggle_en_carro', args=[self.item.id])

        respuesta = self.client.post(url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json()['en_carro'])
        self.item.refresh_from_db()
        self.assertTrue(self.item.en_carro)

        respuesta = self.client.post(url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.json()['en_carro'])
        self.item.refresh_from_db()
        self.assertFalse(self.item.en_carro)

    def test_item_de_otro_usuario_devuelve_404(self):
        self.client.force_login(self.usuario)
        otro = crear_usuario('otro')
        lista_ajena = crear_lista(otro, crear_supermercado(otro, nombre='Ajeno'))
        item_ajeno = crear_item(lista_ajena, 'pan')
        respuesta = self.client.post(
            reverse('compra:toggle_en_carro', args=[item_ajeno.id])
        )
        self.assertEqual(respuesta.status_code, 404)


class EliminarProductoTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario()
        self.supermercado = crear_supermercado(self.usuario)
        self.lista = crear_lista(self.usuario, self.supermercado)
        self.item = crear_item(self.lista, 'leche')

    def test_elimina_el_item(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.post(
            reverse('compra:eliminar_producto', args=[self.item.id])
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(ListaItem.objects.filter(id=self.item.id).exists())

    def test_item_de_otro_usuario_devuelve_404(self):
        self.client.force_login(self.usuario)
        otro = crear_usuario('otro')
        lista_ajena = crear_lista(otro, crear_supermercado(otro, nombre='Ajeno'))
        item_ajeno = crear_item(lista_ajena, 'pan')
        respuesta = self.client.post(
            reverse('compra:eliminar_producto', args=[item_ajeno.id])
        )
        self.assertEqual(respuesta.status_code, 404)


class VaciarListaTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario()
        self.supermercado = crear_supermercado(self.usuario)
        self.lista = crear_lista(self.usuario, self.supermercado)

    def test_vaciar_lista_borra_todos(self):
        self.client.force_login(self.usuario)
        crear_item(self.lista, 'leche')
        crear_item(self.lista, 'pan', en_carro=True)
        respuesta = self.client.post(
            reverse('compra:vaciar_lista', args=[self.lista.id])
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(ListaItem.objects.filter(lista=self.lista).count(), 0)

    def test_vaciar_marcados_solo_borra_en_carro(self):
        self.client.force_login(self.usuario)
        crear_item(self.lista, 'leche')
        crear_item(self.lista, 'pan', en_carro=True)
        crear_item(self.lista, 'atún', en_carro=True)
        respuesta = self.client.post(
            reverse('compra:vaciar_marcados', args=[self.lista.id])
        )
        self.assertEqual(respuesta.status_code, 200)
        nombres = set(
            ListaItem.objects.filter(lista=self.lista)
            .values_list('nombre', flat=True)
        )
        self.assertEqual(nombres, {'leche'})

    def test_lista_de_otro_usuario_devuelve_404(self):
        self.client.force_login(self.usuario)
        otro = crear_usuario('otro')
        ajeno = crear_lista(otro, crear_supermercado(otro, nombre='Ajeno'))
        respuesta = self.client.post(
            reverse('compra:vaciar_lista', args=[ajeno.id])
        )
        self.assertEqual(respuesta.status_code, 404)


class AsignarPasilloTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario()
        self.supermercado = crear_supermercado(self.usuario)
        self.lista = crear_lista(self.usuario, self.supermercado)
        self.item = crear_item(self.lista, 'leche')
        self.pasillo = crear_pasillo(self.supermercado, nombre='Lácteos', orden=1)

    def _post(self, item_id, pasillo_id):
        return self.client.post(
            reverse('compra:asignar_pasillo', args=[item_id]),
            data=json.dumps({'pasillo_id': pasillo_id}),
            content_type='application/json',
        )

    def test_asigna_pasillo_y_crea_keyword(self):
        self.client.force_login(self.usuario)
        respuesta = self._post(self.item.id, self.pasillo.id)
        self.assertEqual(respuesta.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.pasillo, self.pasillo)
        self.assertTrue(
            Keyword.objects.filter(pasillo=self.pasillo, palabra='leche').exists()
        )

    def test_limpia_keyword_de_otros_pasillos(self):
        self.client.force_login(self.usuario)
        pasillo_otro = crear_pasillo(self.supermercado, nombre='Otro', orden=2)
        crear_keyword(pasillo_otro, 'leche')
        respuesta = self._post(self.item.id, self.pasillo.id)
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(
            Keyword.objects.filter(pasillo=self.pasillo, palabra='leche').exists()
        )
        self.assertFalse(
            Keyword.objects.filter(pasillo=pasillo_otro, palabra='leche').exists()
        )

    def test_pasillo_id_vacio_devuelve_400(self):
        self.client.force_login(self.usuario)
        respuesta = self._post(self.item.id, '')
        self.assertEqual(respuesta.status_code, 400)

    def test_pasillo_de_otro_usuario_devuelve_404(self):
        self.client.force_login(self.usuario)
        otro = crear_usuario('otro')
        pasillo_ajeno = crear_pasillo(crear_supermercado(otro, nombre='Ajeno'))
        respuesta = self._post(self.item.id, pasillo_ajeno.id)
        self.assertEqual(respuesta.status_code, 404)

    def test_item_de_otro_usuario_devuelve_404(self):
        self.client.force_login(self.usuario)
        otro = crear_usuario('otro')
        lista_ajena = crear_lista(otro, crear_supermercado(otro, nombre='Ajeno'))
        item_ajeno = crear_item(lista_ajena, 'pan')
        respuesta = self._post(item_ajeno.id, self.pasillo.id)
        self.assertEqual(respuesta.status_code, 404)


class AnalizarFotoTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario()
        self.supermercado = crear_supermercado(self.usuario)
        self.lista = crear_lista(self.usuario, self.supermercado)

    def _foto(self, contenido=b'foto-falsa'):
        return SimpleUploadedFile('lista.jpg', contenido, content_type='image/jpeg')

    def _post(self, lista_id, foto):
        return self.client.post(
            reverse('compra:analizar_foto'),
            {'lista_id': lista_id, 'foto': foto},
        )

    @patch('compra.services.leer_lista_desde_imagen')
    def test_crea_items_y_devuelve_ok(self, mock_ia):
        mock_ia.return_value = (['leche', 'pan'], None)
        self.client.force_login(self.usuario)
        respuesta = self._post(self.lista.id, self._foto())
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertTrue(datos['ok'])
        self.assertEqual(datos['productos_añadidos'], 2)
        self.assertEqual(
            set(
                ListaItem.objects.filter(lista=self.lista)
                .values_list('nombre', flat=True)
            ),
            {'leche', 'pan'},
        )

    @patch('compra.services.leer_lista_desde_imagen')
    def test_sin_foto_devuelve_400(self, mock_ia):
        mock_ia.return_value = (['leche'], None)
        self.client.force_login(self.usuario)
        respuesta = self.client.post(
            reverse('compra:analizar_foto'),
            {'lista_id': self.lista.id},
        )
        self.assertEqual(respuesta.status_code, 400)

    @patch('compra.services.leer_lista_desde_imagen')
    def test_sin_lista_id_devuelve_400(self, mock_ia):
        mock_ia.return_value = (['leche'], None)
        self.client.force_login(self.usuario)
        respuesta = self._post('', self._foto())
        self.assertEqual(respuesta.status_code, 400)

    @patch('compra.services.leer_lista_desde_imagen')
    def test_error_de_ia_devuelve_500(self, mock_ia):
        mock_ia.return_value = (None, 'Error del servicio de IA')
        self.client.force_login(self.usuario)
        respuesta = self._post(self.lista.id, self._foto())
        self.assertEqual(respuesta.status_code, 500)
        self.assertIn('Error del servicio de IA', respuesta.json()['error'])

    @patch('compra.services.leer_lista_desde_imagen')
    def test_valueerror_de_ia_devuelve_400(self, mock_ia):
        mock_ia.side_effect = ValueError('Imagen no válida')
        self.client.force_login(self.usuario)
        respuesta = self._post(self.lista.id, self._foto())
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('Imagen no válida', respuesta.json()['error'])
