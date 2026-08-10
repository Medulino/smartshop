"""Endurecimiento de seguridad: límites de intentos de login/registro y
contadores de uso, respaldados en la base de datos para que funcionen
de forma consistente entre todos los workers de gunicorn (a diferencia de
la caché en memoria, que es por proceso).

Los contadores se guardan en el modelo IntentoFallo con una "ventana"
de tiempo: si pasa la ventana desde el último uso, el contador se reinicia.
"""
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import IntentoFallo

VENTANA_LOGIN_SEGUNDOS = 900  # 15 minutos
VENTANA_REGISTRO_SEGUNDOS = 3600  # 1 hora

LIMITE_LOGIN_EMAIL_IP = 5
LIMITE_LOGIN_IP = 20
LIMITE_ADMIN_LOGIN_IP = 10
LIMITE_REGISTRO_IP = 5
LIMITE_REENVIO_ACTIVACION_IP = 3

INTENTOS_POR_MES = 1_000_000


def obtener_ip(request):
    """IP real del cliente. Solo se confía en X-Forwarded-For si la conexión
    proviene de un proxy de TRUSTED_PROXIES o llega por HTTPS (producción tras
    proxy y con CONFIAR_XFF_EN_HTTPS activo). En otro caso se usa REMOTE_ADDR,
    que el cliente no puede falsificar (evita esquivar los rate limits con un
    header inventado)."""
    remoto = request.META.get('REMOTE_ADDR', 'desconocida')
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if not xff:
        return remoto
    proxy_confiable = remoto in settings.TRUSTED_PROXIES
    https_tras_proxy = request.is_secure() and settings.CONFIAR_XFF_EN_HTTPS
    if proxy_confiable or https_tras_proxy:
        # El proxy añade la IP real al FINAL de la cabecera; la izquierda es
        # la que puede inventar el atacante. Usar la de la derecha evita que
        # un cliente falsifique la IP y esquive los rate limits.
        return xff.split(',')[-1].strip() or remoto
    return remoto


def _acotar(base, max_len=255):
    """Evita que un valor de entrada gigante (p.ej. un email de 300 chars)
    haga saltar el límite varchar(255) de IntentoFallo.base y rompa la
    petición con un 500."""
    return base[:max_len]


def _intentos(base):
    base = _acotar(base)
    try:
        return IntentoFallo.objects.get(base=base).intentos
    except IntentoFallo.DoesNotExist:
        return 0


def _registrar(base, ventana_segundos):
    """Suma 1 al contador de `base` y devuelve el total acumulado."""
    base = _acotar(base)
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


# --- Reenvío del email de activación ---

def reenvio_activacion_bloqueado(ip):
    return _intentos(f"reenvio_activacion_ip_{ip}") >= LIMITE_REENVIO_ACTIVACION_IP


def registrar_reenvio_activacion(ip):
    _registrar(f"reenvio_activacion_ip_{ip}", VENTANA_REGISTRO_SEGUNDOS)
