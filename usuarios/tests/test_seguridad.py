from django.test import TestCase, RequestFactory
from django.urls import reverse

from usuarios import seguridad
from usuarios.models import Usuario, IntentoFallo
from compra.tests.utils import crear_usuario


def _datos_registro(username='nuevo', email='nuevo@test.com', password='clave12345'):
    return {
        'username': username,
        'email': email,
        'password1': password,
        'password2': password,
    }


class OpenRedirectTests(TestCase):
    """El parámetro ?next= no puede redirigir a hosts externos (phishing)."""

    def setUp(self):
        self.usuario = crear_usuario(email='login@test.com')

    def _login_con_next(self, next_url):
        return self.client.post(
            reverse('usuarios:login') + '?next=' + next_url,
            {'email': self.usuario.email, 'password': 'clave12345'},
        )

    def test_next_externo_devuelve_a_compra_lista(self):
        respuesta = self._login_con_next('https://malicioso.com/phish')
        self.assertRedirects(respuesta, reverse('compra:lista'))

    def test_next_scheme_relative_se_rechaza(self):
        respuesta = self._login_con_next('//malicioso.com/phish')
        self.assertRedirects(respuesta, reverse('compra:lista'))

    def test_next_interno_se_respeta(self):
        destino = reverse('compra:configuracion')
        respuesta = self._login_con_next(destino)
        self.assertRedirects(respuesta, destino)

    def test_next_con_credenciales_incorrectas_no_redirige(self):
        respuesta = self.client.post(
            reverse('usuarios:login') + '?next=https://malicioso.com/phish',
            {'email': self.usuario.email, 'password': 'incorrecta'},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Email o contraseña incorrectos.')


class BruteForceLoginTests(TestCase):
    """Bloqueo temporal tras demasiados intentos fallidos de login."""

    def setUp(self):
        self.usuario = crear_usuario(email='brute@test.com')

    def test_bloqueo_tras_5_intentos_fallidos(self):
        for _ in range(5):
            self.client.post(reverse('usuarios:login'), {
                'email': self.usuario.email, 'password': 'incorrecta',
            })
        respuesta = self.client.post(reverse('usuarios:login'), {
            'email': self.usuario.email, 'password': 'clave12345',
        })
        self.assertEqual(respuesta.status_code, 429)
        self.assertContains(respuesta, 'Demasiados intentos.', status_code=429)
        # Aunque la contraseña sea correcta, no se ha logueado
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_correcto_resetea_el_contador(self):
        for _ in range(4):
            self.client.post(reverse('usuarios:login'), {
                'email': self.usuario.email, 'password': 'incorrecta',
            })
        respuesta = self.client.post(reverse('usuarios:login'), {
            'email': self.usuario.email, 'password': 'clave12345',
        })
        self.assertEqual(respuesta.status_code, 302)
        # El contador por email se ha borrado tras el login correcto
        self.assertFalse(IntentoFallo.objects.filter(
            base__startswith=f'login_{self.usuario.email}_'
        ).exists())

    def test_bloqueo_por_ip_tras_muchos_emails_distintos(self):
        for i in range(20):
            self.client.post(reverse('usuarios:login'), {
                'email': f'varias{i}@test.com', 'password': 'incorrecta',
            })
        respuesta = self.client.post(reverse('usuarios:login'), {
            'email': 'otromas@test.com', 'password': 'incorrecta',
        })
        self.assertEqual(respuesta.status_code, 429)


class PasswordValidatorsTests(TestCase):
    """El registro aplica las políticas de contraseña del proyecto."""

    def test_password_numerica_rechazada(self):
        respuesta = self.client.post(
            reverse('usuarios:registro'),
            _datos_registro(password='12345678'),
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'numérica')
        self.assertFalse(Usuario.objects.filter(username='nuevo').exists())

    def test_password_comun_rechazada(self):
        respuesta = self.client.post(
            reverse('usuarios:registro'),
            _datos_registro(password='password'),
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'común')
        self.assertFalse(Usuario.objects.filter(username='nuevo').exists())

    def test_password_valida_con_registro_correcto(self):
        respuesta = self.client.post(
            reverse('usuarios:registro'),
            _datos_registro(password='clave-muy-segura-2026'),
        )
        self.assertRedirects(respuesta, reverse('usuarios:activacion_pendiente'))
        self.assertTrue(Usuario.objects.filter(username='nuevo').exists())


class EnumeracionEmailsTests(TestCase):
    """El registro no revela si un email concreto tiene cuenta."""

    def test_no_se_revela_que_el_email_esta_registrado(self):
        crear_usuario(username='existente', email='objetivo@test.com')
        respuesta = self.client.post(
            reverse('usuarios:registro'),
            _datos_registro(email='objetivo@test.com'),
        )
        self.assertNotContains(respuesta, 'ya está registrado')
        self.assertNotContains(respuesta, 'objetivo@test.com está')
        self.assertContains(respuesta, 'Ese email o nombre de usuario ya está en uso.')


class RegistroRateLimitTests(TestCase):
    """Límite de registros por IP para frenar la creación masiva de cuentas."""

    def test_bloquea_tras_5_registros_desde_la_misma_ip(self):
        for i in range(5):
            self.client.post(
                reverse('usuarios:registro'),
                _datos_registro(username=f'user{i}', email=f'user{i}@test.com'),
            )
        respuesta = self.client.post(
            reverse('usuarios:registro'),
            _datos_registro(username='saturado', email='saturado@test.com'),
        )
        self.assertEqual(respuesta.status_code, 429)
        self.assertFalse(Usuario.objects.filter(username='saturado').exists())


class AdminLoginRateLimitTests(TestCase):
    """El login del admin de Django también está limitado por IP."""

    def setUp(self):
        self.url_login_admin = reverse('admin:login')

    def test_bloquea_el_login_del_admin_tras_10_intentos(self):
        datos = {'username': 'admin@test.com', 'password': 'incorrecta'}
        for _ in range(10):
            self.client.post(self.url_login_admin, datos)
        respuesta = self.client.post(self.url_login_admin, datos)
        self.assertEqual(respuesta.status_code, 429)

    def test_las_demas_peticiones_post_no_se_ven_afectadas(self):
        for _ in range(12):
            self.client.post(self.url_login_admin, {
                'username': 'admin@test.com', 'password': 'incorrecta',
            })
        respuesta = self.client.get(reverse('usuarios:login'))
        self.assertEqual(respuesta.status_code, 200)


class ObtenerIpTests(TestCase):
    """obtener_ip solo confía en X-Forwarded-For si viene de un proxy de fiar
    o de una conexión HTTPS; sobre HTTP se usa REMOTE_ADDR (infalsificable)."""

    def _request(self, remoto, xff=None):
        request = RequestFactory().post('/')
        request.META['REMOTE_ADDR'] = remoto
        if xff is not None:
            request.META['HTTP_X_FORWARDED_FOR'] = xff
        return request

    def test_usa_remoto_cuando_no_hay_xff(self):
        request = self._request('1.2.3.4')
        self.assertEqual(seguridad.obtener_ip(request), '1.2.3.4')

    def test_ignora_xff_sobre_http_sin_proxy_confiable(self):
        request = self._request('1.2.3.4', xff='6.6.6.6')
        self.assertEqual(seguridad.obtener_ip(request), '1.2.3.4')

    def test_usa_xff_desde_proxy_confiable(self):
        with self.settings(TRUSTED_PROXIES=['5.5.5.5']):
            request = self._request('5.5.5.5', xff='6.6.6.6')
            self.assertEqual(seguridad.obtener_ip(request), '6.6.6.6')

    def test_usa_xff_sobre_https(self):
        request = self._request('10.0.0.1', xff='6.6.6.6')
        request.META['wsgi.url_scheme'] = 'https'
        with self.settings(CONFIAR_XFF_EN_HTTPS=True):
            self.assertEqual(seguridad.obtener_ip(request), '6.6.6.6')

    def test_usa_la_ip_real_de_la_derecha_del_xff(self):
        # Un proxy añade la IP real al final de XFF; la izquierda puede ser
        # inventada por el atacante. Siempre debe usarse la de la derecha.
        request = self._request('10.0.0.1', xff='6.6.6.6, 10.0.0.1')
        request.META['wsgi.url_scheme'] = 'https'
        with self.settings(CONFIAR_XFF_EN_HTTPS=True):
            self.assertEqual(seguridad.obtener_ip(request), '10.0.0.1')

    def test_ignora_xff_cuando_confiarse_esta_desactivado(self):
        request = self._request('10.0.0.1', xff='6.6.6.6')
        request.META['wsgi.url_scheme'] = 'https'
        with self.settings(CONFIAR_XFF_EN_HTTPS=False):
            self.assertEqual(seguridad.obtener_ip(request), '10.0.0.1')


class ContentSecurityPolicyTests(TestCase):
    """Todas las respuestas llevan cabecera CSP que solo permite orígenes
    propios (más el CDN de Bootstrap) y bloquea iframes, plugins y navegación
    a sitios ajenos."""

    def _csp(self, respuesta):
        self.assertIn('Content-Security-Policy', respuesta)
        return respuesta['Content-Security-Policy']

    def test_login_lleva_csp_con_restricciones(self):
        csp = self._csp(self.client.get(reverse('usuarios:login')))
        self.assertIn("default-src 'self'", csp)
        self.assertIn("object-src 'none'", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertIn('https://cdn.jsdelivr.net', csp)
        self.assertNotIn('http://', csp)

    def test_paginas_protegidas_llevan_csp(self):
        usuario = crear_usuario()
        self.client.force_login(usuario)
        for url in (reverse('compra:lista'), reverse('usuarios:plan')):
            csp = self._csp(self.client.get(url))
            self.assertIn("default-src 'self'", csp)

    def test_no_se_permite_conectar_a_origenes_externos(self):
        csp = self._csp(self.client.get(reverse('usuarios:login')))
        self.assertIn("connect-src 'self'", csp)
