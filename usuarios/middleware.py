from django.http import HttpResponse

from . import seguridad


class AdminLoginRateLimitMiddleware:
    """Limita por IP los intentos de login del admin de Django."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'POST' and request.path.rstrip('/') == '/admin/login':
            ip = seguridad.obtener_ip(request)
            if seguridad.admin_login_bloqueado(ip):
                return HttpResponse(
                    'Demasiados intentos. Inténtalo más tarde.', status=429
                )
            seguridad.registrar_admin_login(ip)
        return self.get_response(request)
