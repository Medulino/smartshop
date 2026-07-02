from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views import View
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Usuario, PreferenciaUsuario


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

        # Validaciones
        errores = []
        if not username or len(username) < 3:
            errores.append('El nombre de usuario debe tener al menos 3 caracteres.')
        if not email or '@' not in email:
            errores.append('El email no es válido.')
        if len(password1) < 8:
            errores.append('La contraseña debe tener al menos 8 caracteres.')
        if password1 != password2:
            errores.append('Las contraseñas no coinciden.')
        if Usuario.objects.filter(username=username).exists():
            errores.append('Ese nombre de usuario ya está en uso.')
        if Usuario.objects.filter(email=email).exists():
            errores.append('Ese email ya está registrado.')

        if errores:
            return render(request, self.template_name, {
                'errores': errores,
                'username': username,
                'email': email,
            })

        usuario = Usuario.objects.create_user(
            username=username,
            email=email,
            password=password1,
        )
        self._copiar_supermercado_inicial(usuario)

        login(request, usuario)
        messages.success(request, f'¡Bienvenido, {username}! Cuenta creada correctamente.')
        return redirect('compra:lista')
    
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


class LoginView(View):
    template_name = 'usuarios/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('compra:lista')
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        usuario = authenticate(request, username=email, password=password)
        if usuario:
            login(request, usuario)
            next_url = request.GET.get('next', 'compra:lista')
            return redirect(next_url)

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