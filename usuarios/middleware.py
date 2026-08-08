from django.http import HttpResponse
from django.urls import Resolver404, resolve

from . import seguridad


class AdminLoginRateLimitMiddleware:
    """Limita por IP los intentos de login del admin de Django."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'POST' and self._es_login_admin(request):
            ip = seguridad.obtener_ip(request)
            if seguridad.admin_login_bloqueado(ip):
                return HttpResponse(
                    'Demasiados intentos. Inténtalo más tarde.', status=429
                )
            seguridad.registrar_admin_login(ip)
        return self.get_response(request)

    @staticmethod
    def _es_login_admin(request):
        """Detecta la vista de login del admin aunque la URL esté renombrada
        (p.ej. /gestion-ci/), usando el namespace admin en lugar de rutas."""
        try:
            match = resolve(request.path_info)
        except Resolver404:
            return False
        return match.namespace == 'admin' and match.url_name == 'login'
