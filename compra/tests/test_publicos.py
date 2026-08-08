"""Tests de las vistas públicas: Explorar, alternar_like y usar_supermercado_publico."""
import json

from django.test import TestCase
from django.urls import reverse

from compra.tests.utils import (
    crear_usuario, crear_supermercado, crear_pasillo, crear_keyword,
)


def post_json(client, url):
    return client.post(url, data=json.dumps({}), content_type='application/json')


class ExplorarSupermercadosTests(TestCase):

    def setUp(self):
        self.usuario = crear_usuario(username='comprador')
        self.otro_usuario = crear_usuario(username='vendedor')

    def test_sin_login_redirige_al_login(self):
        response = self.client.get(reverse('compra:explorar'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/usuarios/login', response.url)

    def test_solo_muestra_supermercados_publicos_ordenados_por_likes(self):
        self.client.force_login(self.usuario)

        privado = crear_supermercado(self.otro_usuario, nombre='Privado', publico=False)
        publico_1 = crear_supermercado(self.otro_usuario, nombre='Publico 1', publico=True)
        publico_2 = crear_supermercado(self.otro_usuario, nombre='Publico 2', publico=True)

        publico_1.likes.add(self.usuario, self.otro_usuario)
        publico_2.likes.add(self.usuario)
        privado.likes.add(self.otro_usuario)

        response = self.client.get(reverse('compra:explorar'))

        nombres = [s.nombre for s in response.context['supermercados']]
        self.assertEqual(nombres, ['Publico 1', 'Publico 2'])
        self.assertNotIn('Privado', nombres)

    def test_ya_tengo_contiene_los_supermercados_del_usuario(self):
        self.client.force_login(self.usuario)
        crear_supermercado(self.usuario, nombre='Mi Super')
        crear_supermercado(self.usuario, nombre='Otro Tuyo')
        crear_supermercado(self.otro_usuario, nombre='Del Vecino', publico=True)

        response = self.client.get(reverse('compra:explorar'))
        ya_tengo = response.context['ya_tengo']
        self.assertIn('Mi Super', ya_tengo)
        self.assertIn('Otro Tuyo', ya_tengo)
        self.assertNotIn('Del Vecino', ya_tengo)


class AlternarLikeTests(TestCase):

    def setUp(self):
        self.usuario = crear_usuario(username='comprador')
        self.otro_usuario = crear_usuario(username='vendedor')
        self.dueno = crear_usuario(username='dueno')
        self.publico = crear_supermercado(self.dueno, nombre='Publico', publico=True)

    def post_like(self):
        return post_json(
            self.client,
            reverse('compra:alternar_like', args=[self.publico.id]),
        )

    def test_dar_like_devuelve_te_gusta_true_y_total_1(self):
        self.client.force_login(self.usuario)
        response = self.post_like()
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['te_gusta'])
        self.assertEqual(data['total_likes'], 1)

    def test_dar_like_dos_veces_lo_quita(self):
        self.client.force_login(self.usuario)
        self.post_like()
        response = self.post_like()
        data = response.json()
        self.assertFalse(data['te_gusta'])
        self.assertEqual(data['total_likes'], 0)

    def test_like_a_supermercado_no_publicado_devuelve_404(self):
        privado = crear_supermercado(self.dueno, nombre='Privado', publico=False)
        self.client.force_login(self.usuario)
        response = post_json(
            self.client,
            reverse('compra:alternar_like', args=[privado.id]),
        )
        self.assertEqual(response.status_code, 404)

    def test_dos_usuarios_suman_likes_y_cada_uno_quita_el_suyo(self):
        self.client.force_login(self.usuario)
        r1 = self.post_like()
        self.assertEqual(r1.json()['total_likes'], 1)

        self.client.logout()
        self.client.force_login(self.otro_usuario)
        r2 = self.post_like()
        self.assertEqual(r2.json()['total_likes'], 2)

        r3 = self.post_like()
        self.assertFalse(r3.json()['te_gusta'])
        self.assertEqual(r3.json()['total_likes'], 1)

        self.client.logout()
        self.client.force_login(self.usuario)
        r4 = self.post_like()
        self.assertFalse(r4.json()['te_gusta'])
        self.assertEqual(r4.json()['total_likes'], 0)


class UsarSupermercadoPublicoTests(TestCase):

    def setUp(self):
        self.usuario = crear_usuario(username='comprador')
        self.dueno = crear_usuario(username='dueno')
        self.origen = crear_supermercado(self.dueno, nombre='Mercado Central', publico=True)
        self.pasillo = crear_pasillo(self.origen, nombre='Frutas', orden=1)
        crear_keyword(self.pasillo, 'manzana')
        crear_keyword(self.pasillo, 'platano')

    def post_usar(self, supermercado_id):
        return post_json(
            self.client,
            reverse('compra:usar_supermercado_publico', args=[supermercado_id]),
        )

    def test_copia_pasillos_y_keywords_a_la_cuenta_del_usuario(self):
        self.client.force_login(self.usuario)
        response = self.post_usar(self.origen.id)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['nombre'], 'Mercado Central')

        copia = self.usuario.supermercados.get(nombre='Mercado Central')
        self.assertEqual(copia.pasillos.count(), 1)
        pasillo_copia = copia.pasillos.get()
        self.assertEqual(pasillo_copia.nombre, 'Frutas')
        self.assertEqual(
            set(pasillo_copia.keywords.values_list('palabra', flat=True)),
            {'manzana', 'platano'},
        )

    def test_si_ya_tiene_uno_igual_el_nuevo_se_llama_nombre_2(self):
        self.client.force_login(self.usuario)
        crear_supermercado(self.usuario, nombre='Mercado Central')

        response = self.post_usar(self.origen.id)
        data = response.json()
        self.assertEqual(data['nombre'], 'Mercado Central (2)')
        self.assertTrue(
            self.usuario.supermercados.filter(nombre='Mercado Central (2)').exists()
        )

    def test_origen_no_publicado_devuelve_404(self):
        privado = crear_supermercado(self.dueno, nombre='Privado', publico=False)
        self.client.force_login(self.usuario)
        response = self.post_usar(privado.id)
        self.assertEqual(response.status_code, 404)

    def test_el_origen_no_se_modifica(self):
        self.client.force_login(self.usuario)
        self.post_usar(self.origen.id)

        self.origen.refresh_from_db()
        self.assertEqual(self.origen.usuario, self.dueno)
        self.assertTrue(self.origen.publico)
        self.assertEqual(self.origen.pasillos.count(), 1)
        self.assertEqual(
            set(self.origen.pasillos.first().keywords.values_list('palabra', flat=True)),
            {'manzana', 'platano'},
        )
        self.assertEqual(self.dueno.supermercados.count(), 1)


class SupermercadoPropioPublicadoTests(TestCase):
    """Documenta el comportamiento actual: un usuario puede explorar y dar
    like a sus propios supermercados publicados."""

    def setUp(self):
        self.usuario = crear_usuario(username='comprador')

    def test_el_propio_supermercado_publicado_aparece_en_explorar(self):
        self.client.force_login(self.usuario)
        propio = crear_supermercado(self.usuario, nombre='Mi Publicado', publico=True)

        response = self.client.get(reverse('compra:explorar'))
        nombres = [s.nombre for s in response.context['supermercados']]
        self.assertIn('Mi Publicado', nombres)
        self.assertIn('Mi Publicado', response.context['ya_tengo'])

    def test_el_dueno_puede_dar_like_a_su_propio_supermercado_publicado(self):
        self.client.force_login(self.usuario)
        propio = crear_supermercado(self.usuario, nombre='Mi Publicado', publico=True)

        response = post_json(
            self.client,
            reverse('compra:alternar_like', args=[propio.id]),
        )
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['te_gusta'])
        self.assertEqual(data['total_likes'], 1)
