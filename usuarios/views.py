from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.conf import settings
from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.views import View
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.utils import timezone
from datetime import timedelta
import logging
from .models import Usuario, PreferenciaUsuario
from . import seguridad

logger = logging.getLogger(__name__)


class RegistroView(View):
    template_name = 'usuarios/registro.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('compra:lista')
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        ip = seguridad.obtener_ip(request)
        if seguridad.registro_bloqueado(ip):
            return render(request, self.template_name, {
                'errores': ['Demasiados registros desde tu conexión. Inténtalo más tarde.'],
                'username': username,
                'email': email,
            }, status=429)

        # Validaciones
        errores = []
        if not username or len(username) < 3:
            errores.append('El nombre de usuario debe tener al menos 3 caracteres.')
        if len(username) > 150:
            errores.append('El nombre de usuario es demasiado largo.')
        if not email or '@' not in email or len(email) > 254:
            errores.append('El email no es válido.')
        elif self._dominio_temporal(email):
            errores.append('Correo no permitido, usa otro.')
        if len(password1) < 8:
            errores.append('La contraseña debe tener al menos 8 caracteres.')
        if password1 != password2:
            errores.append('Las contraseñas no coinciden.')
        if Usuario.objects.filter(username=username).exists() or \
                Usuario.objects.filter(email=email).exists():
            errores.append('Ese email o nombre de usuario ya está en uso.')

        # Políticas de contraseña del proyecto (evita '12345678', 'password', ...)
        if password1 == password2 and password1:
            try:
                validate_password(
                    password1,
                    user=Usuario(username=username, email=email),
                )
            except ValidationError as e:
                errores.extend(e.messages)

        if errores:
            return render(request, self.template_name, {
                'errores': errores,
                'username': username,
                'email': email,
            })

        seguridad.registrar_registro(ip)
        usuario = Usuario.objects.create_user(
            username=username,
            email=email,
            password=password1,
        )
        # La cuenta nace inactiva hasta que confirme el email (24 h).
        usuario.is_active = False
        usuario.save(update_fields=['is_active'])
        self._copiar_supermercado_inicial(usuario)

        enlace = _enviar_email_activacion(usuario, request)
        request.session['email_activacion'] = usuario.email
        request.session['enlace_activacion'] = enlace

        return redirect('usuarios:activacion_pendiente')

    @staticmethod
    def _dominio_temporal(email):
        try:
            dominio = email.rsplit('@', 1)[1].lower()
        except IndexError:
            return False
        return dominio in settings.DOMINIOS_TEMPORALES

    def _copiar_supermercado_inicial(self, usuario):
        """
        Copia 'Mi Super del Barrio' del superusuario como punto de
        partida para el usuario nuevo, con todos sus pasillos y keywords.
        """
        from compra.models import Supermercado, Pasillo, Keyword

        plantilla = Supermercado.objects.filter(
            usuario__is_superuser=True,
            nombre="Mi Super del Barrio"
        ).first()

        if not plantilla:
            return

        nuevo_super = Supermercado.objects.create(
            usuario=usuario,
            nombre="Mi Super del Barrio",
            direccion='',
            activo=True
        )

        for pasillo_original in plantilla.pasillos.all():
            nuevo_pasillo = Pasillo.objects.create(
                supermercado=nuevo_super,
                nombre=pasillo_original.nombre,
                orden=pasillo_original.orden
            )
            keywords = [
                Keyword(pasillo=nuevo_pasillo, palabra=kw.palabra)
                for kw in pasillo_original.keywords.all()
            ]
            Keyword.objects.bulk_create(keywords, ignore_conflicts=True)


def _enviar_email_activacion(usuario, request):
    """Genera el enlace de activación (caduca en 24 h) y lo envía por email.
    Devuelve el enlace por si el modo consola lo muestra en pantalla."""
    uidb64 = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = default_token_generator.make_token(usuario)
    enlace = request.build_absolute_uri(
        reverse('usuarios:activar_cuenta', args=[uidb64, token])
    )
    asunto = 'Activa tu cuenta — Compra Inteligente'
    mensaje = render_to_string('usuarios/activar_cuenta_email.txt', {
        'usuario': usuario,
        'enlace': enlace,
    })
    try:
        send_mail(asunto, mensaje, None, [usuario.email], fail_silently=False)
    except Exception:
        logger.exception('No se pudo enviar el email de activación a %s', usuario.email)
    return enlace


def _premium_primer_mes_gratis(usuario):
    """Estrategia de captación: el primer mes de cada cuenta nueva es
    premium gratis; al caducar vuelve automáticamente al plan básico."""
    usuario.premium_hasta = timezone.now() + timedelta(days=30)
    usuario.save(update_fields=['premium_hasta'])


class LoginView(View):
    template_name = 'usuarios/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('compra:lista')
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get('email', '').strip().lower()[:254]
        password = request.POST.get('password', '')

        ip = seguridad.obtener_ip(request)
        if seguridad.login_bloqueado(email, ip):
            return render(request, self.template_name, {
                'error': 'Demasiados intentos. Espera unos minutos antes de volver a intentarlo.',
                'email': email,
            }, status=429)

        usuario = authenticate(request, username=email, password=password)
        if usuario:
            login(request, usuario)
            seguridad.resetear_login(email, ip)
            next_url = request.GET.get('next', 'compra:lista')
            # Evita open redirect: solo admite rutas internas del propio host
            if not url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                next_url = 'compra:lista'
            return redirect(next_url)

        # Si el email existe pero la cuenta no se ha activado aún, mensaje
        # específico (no cuenta como fallo de login).
        if Usuario.objects.filter(email=email, is_active=False).exists():
            return render(request, self.template_name, {
                'error': 'Tu cuenta aún no está activada. Revisa tu correo '
                         '(y el spam) o reenvía el enlace de activación.',
                'email': email,
            })

        seguridad.registrar_fallo_login(email, ip)
        return render(request, self.template_name, {
            'error': 'Email o contraseña incorrectos.',
            'email': email,
        })


class LogoutView(View):
    def post(self, request):
        logout(request)
        return redirect('usuarios:login')
    

@login_required
@require_POST
def completar_onboarding(request):
    """Marca que el usuario ya ha visto la guía de bienvenida."""
    prefs, _ = PreferenciaUsuario.objects.get_or_create(usuario=request.user)
    prefs.onboarding_completado = True
    prefs.save()
    return JsonResponse({'ok': True})


@login_required
def premium(request):
    """Página de venta del plan Premium.

    Sin pasarela de pago todavía: por ahora activamos la suscripción de
    forma manual (comando 'conceder_premium' o desde el admin). Cuando
    llegue el cobro automático, esta página será la que cierre la compra.
    """
    return render(request, 'usuarios/premium.html', {
        'usuario': request.user,
    })


@login_required
def plan(request):
    """Comparativa Básico vs Premium (sustituye a la antigua guía de
    bienvenida). Se muestra automáticamente la primera vez hasta que el
    usuario la cierra (marca el onboarding como completado)."""
    return render(request, 'usuarios/plan.html', {
        'usuario': request.user,
    })


def activacion_pendiente(request):
    """Página que se muestra justo tras registrarse: la cuenta está inactiva
    hasta que se confirme el email. Si no hay SMTP configurado (backend de
    consola), se muestra el enlace directamente para poder probar en local."""
    smtp_configurado = bool(settings.EMAIL_HOST_USER)
    return render(request, 'usuarios/activacion_pendiente.html', {
        'email': request.session.get('email_activacion', ''),
        'enlace': request.session.get('enlace_activacion', '') if not smtp_configurado else '',
        'smtp_configurado': smtp_configurado,
    })


@require_POST
def reenviar_activacion(request):
    """Reenvía el email de activación de una cuenta inactiva (máx. 3/hora)."""
    email = (request.POST.get('email', '') or
             request.session.get('email_activacion', '')).strip().lower()
    ip = seguridad.obtener_ip(request)

    if seguridad.reenvio_activacion_bloqueado(ip):
        messages.error(request, 'Demasiados reenvíos. Espera un rato e inténtalo de nuevo.')
        return redirect('usuarios:activacion_pendiente')

    usuario = Usuario.objects.filter(email=email, is_active=False).first()
    if not usuario:
        messages.info(
            request,
            'Si esa cuenta existe y está pendiente de activar, recibirás el enlace.'
        )
        return redirect('usuarios:activacion_pendiente')

    seguridad.registrar_reenvio_activacion(ip)
    enlace = _enviar_email_activacion(usuario, request)
    request.session['email_activacion'] = usuario.email
    request.session['enlace_activacion'] = enlace
    messages.success(request, 'Hemos reenviado el enlace de activación. Revisa tu correo.')
    return redirect('usuarios:activacion_pendiente')


def activar_cuenta(request, uidb64, token):
    """Activa la cuenta desde el enlace del email (caduca en 24 h)."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        usuario = Usuario.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist):
        usuario = None

    if (usuario is None or usuario.is_active
            or not default_token_generator.check_token(usuario, token)):
        return render(request, 'usuarios/activar_cuenta_invalido.html', status=400)

    usuario.is_active = True
    usuario.save(update_fields=['is_active'])
    if not usuario.premium_hasta:
        _premium_primer_mes_gratis(usuario)
    login(request, usuario)
    request.session.pop('email_activacion', None)
    request.session.pop('enlace_activacion', None)
    messages.success(
        request,
        f'¡Bienvenido, {usuario.username}! Cuenta activada correctamente. '
        f'🎁 Disfrutas de tu primer mes Premium gratis.',
    )
    return redirect('compra:lista')