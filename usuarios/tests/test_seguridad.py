from django.test import TestCase
from django.urls import reverse

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
        self.assertRedirects(respuesta, reverse('compra:lista'))
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

    def test_bloquea_el_login_del_admin_tras_10_intentos(self):
        datos = {'username': 'admin@test.com', 'password': 'incorrecta'}
        for _ in range(10):
            self.client.post('/admin/login/', datos)
        respuesta = self.client.post('/admin/login/', datos)
        self.assertEqual(respuesta.status_code, 429)

    def test_las_demas_peticiones_post_no_se_ven_afectadas(self):
        for _ in range(12):
            self.client.post('/admin/login/', {
                'username': 'admin@test.com', 'password': 'incorrecta',
            })
        respuesta = self.client.get(reverse('usuarios:login'))
        self.assertEqual(respuesta.status_code, 200)
