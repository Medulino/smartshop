"""Endurecimiento de seguridad: límites de intentos de login/registro y
contadores de uso, respaldados en la base de datos para que funcionen
de forma consistente entre todos los workers de gunicorn (a diferencia de
la caché en memoria, que es por proceso).

Los contadores se guardan en el modelo IntentoFallo con una "ventana"
de tiempo: si pasa la ventana desde el último uso, el contador se reinicia.
"""
from datetime import timedelta

from django.utils import timezone

from .models import IntentoFallo

VENTANA_LOGIN_SEGUNDOS = 900  # 15 minutos
VENTANA_REGISTRO_SEGUNDOS = 3600  # 1 hora

LIMITE_LOGIN_EMAIL_IP = 5
LIMITE_LOGIN_IP = 20
LIMITE_ADMIN_LOGIN_IP = 10
LIMITE_REGISTRO_IP = 5

INTENTOS_POR_MES = 1_000_000


def obtener_ip(request):
    """IP real del cliente, teniendo en cuenta proxies (X-Forwarded-For)."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip() or 'desconocida'
    return request.META.get('REMOTE_ADDR', 'desconocida')


def _intentos(base):
    try:
        return IntentoFallo.objects.get(base=base).intentos
    except IntentoFallo.DoesNotExist:
        return 0


def _registrar(base, ventana_segundos):
    """Suma 1 al contador de `base` y devuelve el total acumulado."""
    registro, creado = IntentoFallo.objects.get_or_create(
        base=base, defaults={'intentos': 1}
    )
    if not creado:
        if timezone.now() - registro.ultimo_intento > timedelta(seconds=ventana_segundos):
            registro.intentos = 1
        else:
            registro.intentos += 1
        registro.save()
    return registro.intentos


def _resetear(base):
    IntentoFallo.objects.filter(base=base).delete()


def supero_limite(base, limite, ventana_segundos):
    """Devuelve True si el contador de `base` supera `limite` en la ventana."""
    return _registrar(base, ventana_segundos) > limite


# --- Login de la aplicación ---

def login_bloqueado(identificador, ip):
    if _intentos(f"login_{identificador}_{ip}") >= LIMITE_LOGIN_EMAIL_IP:
        return True
    if _intentos(f"login_ip_{ip}") >= LIMITE_LOGIN_IP:
        return True
    return False


def registrar_fallo_login(identificador, ip):
    _registrar(f"login_{identificador}_{ip}", VENTANA_LOGIN_SEGUNDOS)
    _registrar(f"login_ip_{ip}", VENTANA_LOGIN_SEGUNDOS)


def resetear_login(identificador, ip):
    _resetear(f"login_{identificador}_{ip}")


# --- Login del admin de Django ---

def admin_login_bloqueado(ip):
    return _intentos(f"admin_ip_{ip}") >= LIMITE_ADMIN_LOGIN_IP


def registrar_admin_login(ip):
    _registrar(f"admin_ip_{ip}", VENTANA_LOGIN_SEGUNDOS)


# --- Registro de usuarios ---

def registro_bloqueado(ip):
    return _intentos(f"registro_ip_{ip}") >= LIMITE_REGISTRO_IP


def registrar_registro(ip):
    _registrar(f"registro_ip_{ip}", VENTANA_REGISTRO_SEGUNDOS)
