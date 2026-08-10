from datetime import timedelta

from django.core import mail
from django.core.management import call_command
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from compra.models import Supermercado, Pasillo, Keyword
from compra.tests.utils import (
    crear_usuario,
    crear_superusuario,
    crear_supermercado,
    crear_pasillo,
    crear_keyword,
)
from usuarios.models import Usuario, PreferenciaUsuario


class RegistroViewTests(TestCase):
    def test_get_con_usuario_logueado_redirige_a_compra_lista(self):
        usuario = crear_usuario()
        self.client.force_login(usuario)
        respuesta = self.client.get(reverse('usuarios:registro'))
        self.assertRedirects(respuesta, reverse('compra:lista'))

    def test_get_sin_login_renderiza_formulario(self):
        respuesta = self.client.get(reverse('usuarios:registro'))
        self.assertEqual(respuesta.status_code, 200)

    def test_post_valido_crea_usuario_inactivo_envia_email_y_no_loguea(self):
        respuesta = self.client.post(reverse('usuarios:registro'), {
            'username': 'nuevo',
            'email': 'nuevo@test.com',
            'password1': 'clave12345',
            'password2': 'clave12345',
        })
        self.assertRedirects(respuesta, reverse('usuarios:activacion_pendiente'))
        usuario = Usuario.objects.get(username='nuevo')
        self.assertTrue(PreferenciaUsuario.objects.filter(usuario=usuario).exists())
        self.assertFalse(usuario.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Activa tu cuenta', mail.outbox[0].subject)
        self.assertIn('activar', mail.outbox[0].body)
        # No queda autenticado tras registrarse
        protegida = self.client.get(reverse('compra:lista'))
        self.assertEqual(protegida.status_code, 302)

    def test_post_valido_copia_supermercado_con_pasillos_y_keywords(self):
        admin = crear_superusuario()
        plantilla = crear_supermercado(admin, nombre='Mi Super del Barrio')
        pasillo = crear_pasillo(plantilla, nombre='Frutas', orden=1)
        crear_keyword(pasillo, 'manzana')
        crear_keyword(pasillo, 'pera')

        respuesta = self.client.post(reverse('usuarios:registro'), {
            'username': 'nuevo',
            'email': 'nuevo@test.com',
            'password1': 'clave12345',
            'password2': 'clave12345',
        })
        self.assertRedirects(respuesta, reverse('usuarios:activacion_pendiente'))
        usuario = Usuario.objects.get(username='nuevo')
        copia = usuario.supermercados.get(nombre='Mi Super del Barrio')
        pasillos_copia = list(copia.pasillos.values_list('nombre', flat=True))
        self.assertEqual(pasillos_copia, ['Frutas'])
        keywords_copia = list(
            Keyword.objects.filter(pasillo__supermercado=copia).values_list('palabra', flat=True)
        )
        self.assertEqual(sorted(keywords_copia), ['manzana', 'pera'])

    def test_post_sin_supermercado_plantilla_no_falla(self):
        respuesta = self.client.post(reverse('usuarios:registro'), {
            'username': 'nuevo',
            'email': 'nuevo@test.com',
            'password1': 'clave12345',
            'password2': 'clave12345',
        })
        self.assertRedirects(respuesta, reverse('usuarios:activacion_pendiente'))
        usuario = Usuario.objects.get(username='nuevo')
        self.assertEqual(usuario.supermercados.count(), 0)

    def test_post_rechaza_dominio_temporal(self):
        respuesta = self.client.post(reverse('usuarios:registro'), {
            'username': 'nuevo',
            'email': 'nuevo@dnsink.com',
            'password1': 'clave12345',
            'password2': 'clave12345',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Correo no permitido, usa otro.')
        self.assertFalse(Usuario.objects.filter(email='nuevo@dnsink.com').exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_username_demasiado_corto_error(self):
        respuesta = self.client.post(reverse('usuarios:registro'), {
            'username': 'ab',
            'email': 'nuevo@test.com',
            'password1': 'clave12345',
            'password2': 'clave12345',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'El nombre de usuario debe tener al menos 3 caracteres.')
        self.assertFalse(Usuario.objects.filter(username='ab').exists())

    def test_email_invalido_error(self):
        respuesta = self.client.post(reverse('usuarios:registro'), {
            'username': 'nuevo',
            'email': 'correo-sin-arroba',
            'password1': 'clave12345',
            'password2': 'clave12345',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'El email no es válido.')
        self.assertFalse(Usuario.objects.filter(email='correo-sin-arroba').exists())

    def test_password_demasiado_corta_error(self):
        respuesta = self.client.post(reverse('usuarios:registro'), {
            'username': 'nuevo',
            'email': 'nuevo@test.com',
            'password1': 'corta',
            'password2': 'corta',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'La contraseña debe tener al menos 8 caracteres.')
        self.assertFalse(Usuario.objects.filter(username='nuevo').exists())

    def test_passwords_no_coinciden_error(self):
        respuesta = self.client.post(reverse('usuarios:registro'), {
            'username': 'nuevo',
            'email': 'nuevo@test.com',
            'password1': 'clave12345',
            'password2': 'clave54321',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Las contraseñas no coinciden.')
        self.assertFalse(Usuario.objects.filter(username='nuevo').exists())

    def test_username_ya_usado_error(self):
        crear_usuario(username='nuevo', email='otro@test.com')
        respuesta = self.client.post(reverse('usuarios:registro'), {
            'username': 'nuevo',
            'email': 'nuevo@test.com',
            'password1': 'clave12345',
            'password2': 'clave12345',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Ese email o nombre de usuario ya está en uso.')
        self.assertEqual(Usuario.objects.filter(username='nuevo').count(), 1)

    def test_email_ya_registrado_error(self):
        crear_usuario(username='existente', email='nuevo@test.com')
        respuesta = self.client.post(reverse('usuarios:registro'), {
            'username': 'nuevo',
            'email': 'nuevo@test.com',
            'password1': 'clave12345',
            'password2': 'clave12345',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Ese email o nombre de usuario ya está en uso.')
        self.assertFalse(Usuario.objects.filter(username='nuevo').exists())


class LoginViewTests(TestCase):
    def test_get_con_usuario_logueado_redirige_a_compra_lista(self):
        usuario = crear_usuario()
        self.client.force_login(usuario)
        respuesta = self.client.get(reverse('usuarios:login'))
        self.assertRedirects(respuesta, reverse('compra:lista'))

    def test_post_credenciales_correctas_redirige_a_compra_lista(self):
        usuario = crear_usuario(email='login@test.com')
        respuesta = self.client.post(reverse('usuarios:login'), {
            'email': usuario.email,
            'password': 'clave12345',
        })
        self.assertRedirects(respuesta, reverse('compra:lista'))

    def test_post_respeta_next(self):
        usuario = crear_usuario(email='login@test.com')
        destino = reverse('compra:configuracion')
        respuesta = self.client.post(
            reverse('usuarios:login') + '?next=' + destino,
            {'email': usuario.email, 'password': 'clave12345'},
        )
        self.assertRedirects(respuesta, destino)

    def test_post_email_incorrecto_error(self):
        crear_usuario(email='login@test.com')
        respuesta = self.client.post(reverse('usuarios:login'), {
            'email': 'mal@test.com',
            'password': 'clave12345',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Email o contraseña incorrectos.')

    def test_post_password_incorrecto_error(self):
        crear_usuario(email='login@test.com')
        respuesta = self.client.post(reverse('usuarios:login'), {
            'email': 'login@test.com',
            'password': 'password-mala',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Email o contraseña incorrectos.')

    def test_post_cuenta_sin_activar_mensaje_especifico(self):
        usuario = crear_usuario(email='sinactivar@test.com')
        usuario.is_active = False
        usuario.save(update_fields=['is_active'])
        respuesta = self.client.post(reverse('usuarios:login'), {
            'email': usuario.email,
            'password': 'clave12345',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Tu cuenta aún no está activada')


class ActivacionCuentaTests(TestCase):
    def _enlace(self, usuario):
        uidb64 = urlsafe_base64_encode(force_bytes(usuario.pk))
        token = default_token_generator.make_token(usuario)
        return reverse('usuarios:activar_cuenta', args=[uidb64, token])

    def _usuario_inactivo(self, email='activa@test.com'):
        usuario = crear_usuario(email=email)
        usuario.is_active = False
        usuario.save(update_fields=['is_active'])
        return usuario

    def test_activar_cuenta_valida_activa_loguea_y_concede_premium(self):
        usuario = self._usuario_inactivo()
        respuesta = self.client.get(self._enlace(usuario))
        self.assertRedirects(respuesta, reverse('compra:lista'))
        usuario.refresh_from_db()
        self.assertTrue(usuario.is_active)
        self.assertTrue(usuario.es_premium)
        lista = self.client.get(reverse('compra:lista'))
        self.assertEqual(lista.wsgi_request.user, usuario)

    def test_activar_cuenta_token_invalido_muestra_error(self):
        usuario = self._usuario_inactivo()
        uidb64 = urlsafe_base64_encode(force_bytes(usuario.pk))
        respuesta = self.client.get(
            reverse('usuarios:activar_cuenta', args=[uidb64, 'token-malo'])
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertContains(respuesta, 'Enlace no válido o caducado', status_code=400)
        usuario.refresh_from_db()
        self.assertFalse(usuario.is_active)

    def test_activar_cuenta_token_reutilizado_no_vuelve_a_activar(self):
        usuario = self._usuario_inactivo()
        enlace = self._enlace(usuario)
        self.client.get(enlace)
        usuario.refresh_from_db()
        self.assertTrue(usuario.is_active)
        respuesta = self.client.get(enlace)
        self.assertEqual(respuesta.status_code, 400)
        self.assertContains(respuesta, 'Enlace no válido o caducado', status_code=400)


class ReenviarActivacionTests(TestCase):
    def test_reenviar_activacion_envia_email(self):
        usuario = crear_usuario(email='reenvio@test.com')
        usuario.is_active = False
        usuario.save(update_fields=['is_active'])
        respuesta = self.client.post(
            reverse('usuarios:reenviar_activacion'),
            {'email': usuario.email},
        )
        self.assertRedirects(respuesta, reverse('usuarios:activacion_pendiente'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Activa tu cuenta', mail.outbox[0].subject)

    def test_reenviar_activacion_sin_cuenta_no_envia(self):
        respuesta = self.client.post(
            reverse('usuarios:reenviar_activacion'),
            {'email': 'noexiste@test.com'},
        )
        self.assertRedirects(respuesta, reverse('usuarios:activacion_pendiente'))
        self.assertEqual(len(mail.outbox), 0)

    def test_reenviar_activacion_rate_limit(self):
        usuario = crear_usuario(email='reenvio@test.com')
        usuario.is_active = False
        usuario.save(update_fields=['is_active'])
        for _ in range(3):
            self.client.post(reverse('usuarios:reenviar_activacion'), {'email': usuario.email})
        respuesta = self.client.post(
            reverse('usuarios:reenviar_activacion'),
            {'email': usuario.email},
        )
        self.assertRedirects(respuesta, reverse('usuarios:activacion_pendiente'))
        self.assertEqual(len(mail.outbox), 3)


class PurgarInactivosTests(TestCase):
    def test_purga_borra_solo_inactivas_antiguas(self):
        vieja = crear_usuario(username='vieja', email='vieja@test.com')
        vieja.is_active = False
        vieja.save(update_fields=['is_active'])
        Usuario.objects.filter(pk=vieja.pk).update(
            date_joined=timezone.now() - timedelta(days=10)
        )
        reciente = crear_usuario(username='reciente', email='reciente@test.com')
        reciente.is_active = False
        reciente.save(update_fields=['is_active'])
        activa = crear_usuario(username='activa', email='activa@test.com')

        call_command('purgar_inactivos', dias=7)

        self.assertFalse(Usuario.objects.filter(email='vieja@test.com').exists())
        self.assertTrue(Usuario.objects.filter(email='reciente@test.com').exists())
        self.assertTrue(Usuario.objects.filter(email='activa@test.com').exists())



class LogoutViewTests(TestCase):
    def test_post_logout_cierra_sesion_y_redirige_a_login(self):
        usuario = crear_usuario()
        self.client.force_login(usuario)
        respuesta = self.client.post(reverse('usuarios:logout'))
        self.assertRedirects(respuesta, reverse('usuarios:login'))
        protegida = self.client.get(reverse('compra:lista'))
        self.assertEqual(protegida.status_code, 302)


class CompletarOnboardingTests(TestCase):
    def test_post_con_login_marca_onboarding_completado(self):
        usuario = crear_usuario()
        self.client.force_login(usuario)
        respuesta = self.client.post(reverse('usuarios:completar_onboarding'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), {'ok': True})
        usuario.refresh_from_db()
        self.assertTrue(usuario.preferencias.onboarding_completado)

    def test_post_sin_login_redirige_a_login(self):
        respuesta = self.client.post(reverse('usuarios:completar_onboarding'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('usuarios:login'), respuesta.url)


class ListaCompraProtegidaTests(TestCase):
    def test_usuario_no_autenticado_es_redirigido_a_login(self):
        respuesta = self.client.get(reverse('compra:lista'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('usuarios:login'), respuesta.url)


class CambiarPasswordTests(TestCase):
    def test_get_sin_login_redirige_a_login(self):
        respuesta = self.client.get(reverse('usuarios:cambiar_password'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('usuarios:login'), respuesta.url)

    def test_get_con_login_renderiza_formulario(self):
        usuario = crear_usuario()
        self.client.force_login(usuario)
        respuesta = self.client.get(reverse('usuarios:cambiar_password'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Contraseña actual')

    def test_post_valido_cambia_la_contrasena_y_redirige(self):
        usuario = crear_usuario()
        self.client.force_login(usuario)
        respuesta = self.client.post(reverse('usuarios:cambiar_password'), {
            'old_password': 'clave12345',
            'new_password1': 'NuevaClave2026!',
            'new_password2': 'NuevaClave2026!',
        })
        self.assertRedirects(respuesta, reverse('usuarios:cambiar_password_hecho'))
        usuario.refresh_from_db()
        self.assertTrue(usuario.check_password('NuevaClave2026!'))

    def test_post_con_password_actual_incorrecta_muestra_error(self):
        usuario = crear_usuario()
        self.client.force_login(usuario)
        respuesta = self.client.post(reverse('usuarios:cambiar_password'), {
            'old_password': 'clave-mala',
            'new_password1': 'NuevaClave2026!',
            'new_password2': 'NuevaClave2026!',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Su contraseña antigua es incorrecta')
        usuario.refresh_from_db()
        self.assertTrue(usuario.check_password('clave12345'))

    def test_post_passwords_que_no_coinciden_muestra_error(self):
        usuario = crear_usuario()
        self.client.force_login(usuario)
        respuesta = self.client.post(reverse('usuarios:cambiar_password'), {
            'old_password': 'clave12345',
            'new_password1': 'NuevaClave2026!',
            'new_password2': 'OtraClave2026!',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Los dos campos de contraseña no coinciden.')
        usuario.refresh_from_db()
        self.assertTrue(usuario.check_password('clave12345'))
