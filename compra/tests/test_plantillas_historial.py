"""Tests de plantillas e historial: guardar/usar/eliminar plantillas,
repetir y archivar listas, historial y exportación a PDF."""
import json

from django.test import TestCase
from django.urls import reverse

from compra.tests.utils import (
    crear_usuario, crear_supermercado, crear_pasillo, crear_lista, crear_item,
)


def post_json(client, url, data=None):
    return client.post(
        url, data=json.dumps(data or {}), content_type='application/json'
    )


class GuardarComoPlantillaTests(TestCase):

    def setUp(self):
        self.usuario = crear_usuario(username='comprador')
        self.otro_usuario = crear_usuario(username='vecino')
        self.supermercado = crear_supermercado(self.usuario, nombre='Mercado')
        self.lista = crear_lista(self.usuario, self.supermercado, activa=True)
        self.pasillo = crear_pasillo(self.supermercado, nombre='Frutas')
        crear_item(self.lista, 'manzanas', pasillo=self.pasillo)
        crear_item(self.lista, 'platanos', pasillo=self.pasillo)

    def post_guardar(self, lista_id, nombre):
        return post_json(
            self.client,
            reverse('compra:guardar_como_plantilla', args=[lista_id]),
            data={'nombre': nombre},
        )

    def test_crea_plantilla_con_nombre_y_copia_los_items(self):
        self.client.force_login(self.usuario)
        response = self.post_guardar(self.lista.id, 'Compra semanal')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])

        plantilla = self.usuario.listas.get(id=data['plantilla_id'])
        self.assertTrue(plantilla.es_plantilla)
        self.assertEqual(plantilla.nombre_plantilla, 'Compra semanal')
        self.assertFalse(plantilla.activa)
        self.assertEqual(plantilla.supermercado, self.supermercado)
        self.assertEqual(
            set(plantilla.items.values_list('nombre', flat=True)),
            {'manzanas', 'platanos'},
        )
        for item in plantilla.items.all():
            self.assertEqual(item.pasillo, self.pasillo)

    def test_sin_nombre_devuelve_400(self):
        self.client.force_login(self.usuario)
        response = self.post_guardar(self.lista.id, '')
        self.assertEqual(response.status_code, 400)

    def test_lista_de_otro_usuario_devuelve_404(self):
        super_otro = crear_supermercado(self.otro_usuario, nombre='Del vecino')
        lista_otro = crear_lista(self.otro_usuario, super_otro, activa=True)
        self.client.force_login(self.usuario)
        response = self.post_guardar(lista_otro.id, 'Plantilla ajena')
        self.assertEqual(response.status_code, 404)


class UsarPlantillaTests(TestCase):

    def setUp(self):
        self.usuario = crear_usuario(username='comprador')
        self.otro_usuario = crear_usuario(username='vecino')
        self.supermercado = crear_supermercado(self.usuario, nombre='Mercado')
        self.pasillo = crear_pasillo(self.supermercado, nombre='Frutas')
        self.plantilla = crear_lista(
            self.usuario, self.supermercado,
            activa=False, es_plantilla=True, nombre_plantilla='Compra semanal',
        )
        crear_item(self.plantilla, 'manzanas', pasillo=self.pasillo)
        crear_item(self.plantilla, 'platanos', pasillo=self.pasillo)

    def post_usar(self, plantilla_id):
        return post_json(
            self.client,
            reverse('compra:usar_plantilla', args=[plantilla_id]),
        )

    def test_vuelca_los_items_en_la_lista_activa_creandola_si_no_existe(self):
        self.client.force_login(self.usuario)
        self.assertFalse(self.usuario.listas.filter(activa=True).exists())

        response = self.post_usar(self.plantilla.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])

        lista_activa = self.usuario.listas.get(activa=True)
        self.assertEqual(lista_activa.supermercado, self.supermercado)
        self.assertFalse(lista_activa.es_plantilla)
        self.assertEqual(
            set(lista_activa.items.values_list('nombre', flat=True)),
            {'manzanas', 'platanos'},
        )

    def test_no_duplica_productos_ya_existentes_en_la_lista_activa(self):
        self.client.force_login(self.usuario)
        lista_activa = crear_lista(self.usuario, self.supermercado, activa=True)
        crear_item(lista_activa, 'manzanas', pasillo=self.pasillo)

        response = self.post_usar(self.plantilla.id)
        self.assertEqual(response.status_code, 200)

        nombres = list(lista_activa.items.values_list('nombre', flat=True))
        self.assertEqual(len(nombres), 2)
        self.assertCountEqual(nombres, ['manzanas', 'platanos'])

    def test_plantilla_de_otro_usuario_devuelve_404(self):
        super_otro = crear_supermercado(self.otro_usuario, nombre='Del vecino')
        plantilla_otro = crear_lista(
            self.otro_usuario, super_otro,
            activa=False, es_plantilla=True, nombre_plantilla='Ajena',
        )
        self.client.force_login(self.usuario)
        response = self.post_usar(plantilla_otro.id)
        self.assertEqual(response.status_code, 404)

    def test_lista_que_no_es_plantilla_devuelve_404(self):
        lista_normal = crear_lista(self.usuario, self.supermercado, activa=False)
        self.client.force_login(self.usuario)
        response = self.post_usar(lista_normal.id)
        self.assertEqual(response.status_code, 404)


class EliminarPlantillaTests(TestCase):

    def setUp(self):
        self.usuario = crear_usuario(username='comprador')
        self.otro_usuario = crear_usuario(username='vecino')
        self.supermercado = crear_supermercado(self.usuario, nombre='Mercado')
        self.plantilla = crear_lista(
            self.usuario, self.supermercado,
            activa=False, es_plantilla=True, nombre_plantilla='Compra semanal',
        )

    def post_eliminar(self, plantilla_id):
        return post_json(
            self.client,
            reverse('compra:eliminar_plantilla', args=[plantilla_id]),
        )

    def test_borra_la_plantilla(self):
        self.client.force_login(self.usuario)
        response = self.post_eliminar(self.plantilla.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        self.assertFalse(self.usuario.listas.filter(id=self.plantilla.id).exists())

    def test_plantilla_de_otro_usuario_devuelve_404(self):
        super_otro = crear_supermercado(self.otro_usuario, nombre='Del vecino')
        plantilla_otro = crear_lista(
            self.otro_usuario, super_otro,
            activa=False, es_plantilla=True, nombre_plantilla='Ajena',
        )
        self.client.force_login(self.usuario)
        response = self.post_eliminar(plantilla_otro.id)
        self.assertEqual(response.status_code, 404)


class RepetirListaTests(TestCase):

    def setUp(self):
        self.usuario = crear_usuario(username='comprador')
        self.otro_usuario = crear_usuario(username='vecino')
        self.supermercado = crear_supermercado(self.usuario, nombre='Mercado')
        self.pasillo = crear_pasillo(self.supermercado, nombre='Frutas')
        self.archivada = crear_lista(self.usuario, self.supermercado, activa=False)
        crear_item(self.archivada, 'manzanas', pasillo=self.pasillo)
        crear_item(self.archivada, 'pan')

    def post_repetir(self, lista_id):
        return post_json(
            self.client,
            reverse('compra:repetir_lista', args=[lista_id]),
        )

    def test_copia_items_a_la_lista_activa_sin_duplicar(self):
        self.client.force_login(self.usuario)
        lista_activa = crear_lista(self.usuario, self.supermercado, activa=True)
        crear_item(lista_activa, 'manzanas')

        response = self.post_repetir(self.archivada.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])

        nombres = list(lista_activa.items.values_list('nombre', flat=True))
        self.assertCountEqual(nombres, ['manzanas', 'pan'])

    def test_lista_de_otro_usuario_devuelve_404(self):
        super_otro = crear_supermercado(self.otro_usuario, nombre='Del vecino')
        lista_otro = crear_lista(self.otro_usuario, super_otro, activa=False)
        self.client.force_login(self.usuario)
        response = self.post_repetir(lista_otro.id)
        self.assertEqual(response.status_code, 404)


class ArchivarListaTests(TestCase):

    def setUp(self):
        self.usuario = crear_usuario(username='comprador')
        self.otro_usuario = crear_usuario(username='vecino')
        self.supermercado = crear_supermercado(self.usuario, nombre='Mercado')
        self.lista = crear_lista(self.usuario, self.supermercado, activa=True)

    def post_archivar(self, lista_id):
        return post_json(
            self.client,
            reverse('compra:archivar_lista', args=[lista_id]),
        )

    def test_marca_la_lista_como_no_activa(self):
        self.client.force_login(self.usuario)
        response = self.post_archivar(self.lista.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        self.lista.refresh_from_db()
        self.assertFalse(self.lista.activa)

    def test_lista_de_otro_usuario_devuelve_404(self):
        super_otro = crear_supermercado(self.otro_usuario, nombre='Del vecino')
        lista_otro = crear_lista(self.otro_usuario, super_otro, activa=True)
        self.client.force_login(self.usuario)
        response = self.post_archivar(lista_otro.id)
        self.assertEqual(response.status_code, 404)


class HistorialViewTests(TestCase):

    def setUp(self):
        self.usuario = crear_usuario(username='comprador')
        self.otro_usuario = crear_usuario(username='vecino')
        self.supermercado = crear_supermercado(self.usuario, nombre='Mercado')

    def test_solo_muestra_listas_no_activas_y_plantillas(self):
        self.client.force_login(self.usuario)
        activa = crear_lista(self.usuario, self.supermercado, activa=True)
        archivada = crear_lista(self.usuario, self.supermercado, activa=False)
        plantilla = crear_lista(
            self.usuario, self.supermercado,
            activa=False, es_plantilla=True, nombre_plantilla='Compra semanal',
        )
        super_otro = crear_supermercado(self.otro_usuario, nombre='Del vecino')
        lista_otro = crear_lista(self.otro_usuario, super_otro, activa=False)

        response = self.client.get(reverse('compra:historial'))
        listas = response.context['listas']
        plantillas = response.context['plantillas']

        self.assertIn(archivada, listas)
        self.assertNotIn(activa, listas)
        self.assertNotIn(plantilla, listas)
        self.assertNotIn(lista_otro, listas)

        self.assertIn(plantilla, plantillas)
        self.assertNotIn(archivada, plantillas)
        self.assertNotIn(activa, plantillas)

    def test_sin_login_redirige_al_login(self):
        response = self.client.get(reverse('compra:historial'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/usuarios/login', response.url)


class ExportarPdfTests(TestCase):

    def setUp(self):
        self.usuario = crear_usuario(username='comprador')
        self.otro_usuario = crear_usuario(username='vecino')
        self.supermercado = crear_supermercado(self.usuario, nombre='Mercado')
        self.lista = crear_lista(self.usuario, self.supermercado, activa=False)
        crear_item(self.lista, 'manzanas')
        crear_item(self.lista, 'pan')

    def get_pdf(self, lista_id):
        return self.client.get(reverse('compra:exportar_pdf', args=[lista_id]))

    def test_genera_un_pdf_valido(self):
        self.client.force_login(self.usuario)
        response = self.get_pdf(self.lista.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content)
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_lista_de_otro_usuario_devuelve_404(self):
        super_otro = crear_supermercado(self.otro_usuario, nombre='Del vecino')
        lista_otro = crear_lista(self.otro_usuario, super_otro, activa=False)
        self.client.force_login(self.usuario)
        response = self.get_pdf(lista_otro.id)
        self.assertEqual(response.status_code, 404)

    def test_sin_login_redirige_al_login(self):
        response = self.get_pdf(self.lista.id)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/usuarios/login', response.url)
