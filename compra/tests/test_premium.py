"""Tests del plan Premium: candados en la interfaz y bloqueo en el servidor
para los usuarios con plan básico (el superusuario no tiene ventajas)."""
import json

from django.test import TestCase
from django.urls import reverse

from compra.tests.utils import crear_usuario, crear_supermercado, crear_lista, crear_item
from usuarios.models import FeatureFlag


def post_json(client, url, data=None):
    return client.post(
        url, data=json.dumps(data or {}), content_type='application/json'
    )


def activar_flags(*nombres):
    for nombre in nombres:
        FeatureFlag.objects.create(
            nombre=nombre, activo=True, requiere_premium=True
        )
    # La caché de flags (TTL 60s) es compartida entre tests: invalidarla
    # para que cada test parta del estado que acaba de crear.
    from django.core.cache import cache
    cache.clear()


class PlanTests(TestCase):

    def setUp(self):
        self.usuario = crear_usuario(username='plan')
        self.supermercado = crear_supermercado(self.usuario, nombre='Mercado')
        self.lista = crear_lista(self.usuario, self.supermercado, activa=True)
        crear_item(self.lista, 'manzanas')
        activar_flags('historial', 'plantillas', 'exportar_pdf')

    def test_sin_premium_hasta_es_basico(self):
        self.assertFalse(self.usuario.es_premium)

    def test_con_premium_hasta_futuro_es_premium(self):
        from datetime import timedelta
        from django.utils import timezone
        self.usuario.premium_hasta = timezone.now() + timedelta(days=30)
        self.usuario.save(update_fields=['premium_hasta'])
        self.assertTrue(self.usuario.es_premium)
        self.assertGreater(self.usuario.dias_premium_restantes, 0)

    def test_con_premium_hasta_pasado_es_basico(self):
        from datetime import timedelta
        from django.utils import timezone
        self.usuario.premium_hasta = timezone.now() - timedelta(days=1)
        self.usuario.save(update_fields=['premium_hasta'])
        self.assertFalse(self.usuario.es_premium)

    def test_es_premium_ignora_al_superusuario(self):
        """El superusuario NO tiene ventajas automáticas: también se le aplica
        su plan (básico si no tiene premium_hasta)."""
        from compra.tests.utils import crear_superusuario
        admin = crear_superusuario(username='jefazo')
        admin.premium_hasta = None
        admin.save(update_fields=['premium_hasta'])
        self.assertFalse(admin.es_premium)


class BloqueoEnServidorTests(TestCase):

    def setUp(self):
        self.usuario = crear_usuario(username='gratis')
        self.supermercado = crear_supermercado(self.usuario, nombre='Mercado')
        self.lista = crear_lista(self.usuario, self.supermercado, activa=True)
        crear_item(self.lista, 'manzanas')
        activar_flags('historial', 'plantillas', 'exportar_pdf')

    def test_guardar_plantilla_devuelve_403_con_indicio_premium(self):
        self.client.force_login(self.usuario)
        response = post_json(
            self.client,
            reverse('compra:guardar_como_plantilla', args=[self.lista.id]),
            data={'nombre': 'Mi lista'},
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(response.json()['premium'])

    def test_historial_redirige_a_la_pagina_premium(self):
        self.client.force_login(self.usuario)
        response = self.client.get(reverse('compra:historial'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('usuarios:premium'), response.url)

    def test_exportar_pdf_redirige_a_la_pagina_premium(self):
        self.client.force_login(self.usuario)
        response = self.client.get(reverse('compra:exportar_pdf', args=[self.lista.id]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('usuarios:premium'), response.url)


class CandadoEnInterfazTests(TestCase):

    def setUp(self):
        self.usuario = crear_usuario(username='gratis')
        self.supermercado = crear_supermercado(self.usuario, nombre='Mercado')
        self.lista = crear_lista(self.usuario, self.supermercado, activa=True)
        crear_item(self.lista, 'manzanas')
        activar_flags('historial', 'plantillas', 'exportar_pdf')

    def test_usuario_basico_ve_candados_y_no_las_features(self):
        self.client.force_login(self.usuario)
        html = self.client.get(reverse('compra:lista')).content.decode()
        self.assertIn('🔒Mis Listas', html)
        self.assertIn('🔒PDF', html)
        self.assertNotIn('⭐Mis Listas', html)
        self.assertNotIn('📄PDF', html)

    def test_premium_ve_las_features_sin_candados(self):
        from datetime import timedelta
        from django.utils import timezone
        self.usuario.premium_hasta = timezone.now() + timedelta(days=30)
        self.usuario.save(update_fields=['premium_hasta'])
        self.client.force_login(self.usuario)
        html = self.client.get(reverse('compra:lista')).content.decode()
        self.assertIn('⭐Mis Listas', html)
        self.assertIn('📄PDF', html)
        self.assertNotIn('🔒Mis Listas', html)
        self.assertNotIn('🔒PDF', html)
