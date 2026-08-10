
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.cache import cache


class Usuario(AbstractUser):
    """
    Usuario personalizado. Usamos email como identificador principal
    en lugar del username, que es más profesional y cómodo para el usuario.
    """
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    avatar = models.CharField(
        max_length=10,
        default='🛒',
        help_text='Emoji que representa al usuario'
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)
    premium_hasta = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Premium hasta',
        help_text='Fecha en la que caduca el plan premium. Vacío o pasado = plan básico. '
                  'El superusuario NO tiene ventajas automáticas: también se le aplica su plan.'
    )

    # Login con email en vez de username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['-fecha_registro']

    def __str__(self):
        return f"{self.username} ({self.email})"

    @property
    def es_premium(self):
        return bool(self.premium_hasta and self.premium_hasta > timezone.now())

    @property
    def dias_premium_restantes(self):
        if not self.es_premium:
            return 0
        return (self.premium_hasta - timezone.now()).days

    def total_listas(self):
        return self.listas.count()

    def total_productos_añadidos(self):
        from compra.models import ListaItem
        return ListaItem.objects.filter(lista__usuario=self).count()
    
    def save(self, *args, **kwargs):
        es_nuevo = self._state.adding
        super().save(*args, **kwargs)
        if es_nuevo:
            PreferenciaUsuario.objects.get_or_create(usuario=self)

class IntentoFallo(models.Model):
    """
    Contador de intentos fallidos (login, registro, admin) por base única
    (p. ej. 'login_email_ip' o 'login_ip_...'). Respaldado en BD para que
    el límite sea compartido entre todos los workers. Se limpia con el
    comando de gestión 'limpiar_intentos'.
    """
    base = models.CharField(max_length=255, unique=True)
    intentos = models.PositiveIntegerField(default=0)
    ultimo_intento = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Intento fallido'
        verbose_name_plural = 'Intentos fallidos'
        ordering = ['-ultimo_intento']

    def __str__(self):
        return f"{self.base}: {self.intentos} intentos"


class FeatureFlag(models.Model):
    """
    Controla qué funcionalidades están activas.
    Se gestiona desde el admin sin tocar código.
    """
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=False)
    requiere_premium = models.BooleanField(
        default=False,
        help_text='Si está marcado, solo lo usan los usuarios con plan premium '
                  '(el superusuario no tiene ventajas: también necesita premium)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Feature Flag'
        verbose_name_plural = 'Feature Flags'
        ordering = ['nombre']

    def __str__(self):
        estado = '✅' if self.activo else '❌'
        plan = ' [PREMIUM]' if self.requiere_premium else ''
        return f"{estado} {self.nombre}{plan}"

    @classmethod
    def esta_activo(cls, nombre, usuario=None):
        """
        Uso: FeatureFlag.esta_activo('plantillas', request.user)
        Devuelve True si la funcionalidad está activa y el usuario puede usarla
        según su plan.
        """
        try:
            flag = cls.objects.get(nombre=nombre)
            if not flag.activo:
                return False
            if flag.requiere_premium and not (usuario and usuario.es_premium):
                return False
            return True
        except cls.DoesNotExist:
            return False


_FLAGS_CACHE_KEY = 'feature_flags_v2'
_FLAGS_CACHE_TTL = 60


def _flags_cache():
    """(activo, requiere_premium) por flag, en una sola query cacheada.
    Compartido por el context processor y los checks de vista."""
    datos = cache.get(_FLAGS_CACHE_KEY)
    if datos is None:
        datos = {
            f.nombre: (f.activo, f.requiere_premium)
            for f in FeatureFlag.objects.only('nombre', 'activo', 'requiere_premium')
        }
        cache.set(_FLAGS_CACHE_KEY, datos, _FLAGS_CACHE_TTL)
    return datos


def flag_disponible(nombre, usuario):
    """Devuelve (disponible, bloqueado_por_premium) para un flag y un usuario.

    'disponible' es True si el flag está activo Y el usuario puede usarlo según
    su plan. 'bloqueado_por_premium' es True cuando la feature es premium y el
    usuario es básico (para poder mostrar candado en la interfaz)."""
    estado = _flags_cache().get(nombre)
    if not estado:
        return False, False
    activo, requiere_premium = estado
    if not activo:
        return False, False
    if requiere_premium:
        if usuario and usuario.es_premium:
            return True, False
        return False, True
    return True, False
        

class PreferenciaUsuario(models.Model):
    """
    Preferencias personales de cada usuario sobre las funcionalidades.
    Solo tiene efecto si el FeatureFlag global está activo.
    """
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name='preferencias'
    )

    # Interfaz
    mostrar_estadisticas = models.BooleanField(
        default=True,
        verbose_name='Mostrar estadísticas en la pantalla principal'
    )
    mostrar_sugerencias = models.BooleanField(
        default=True,
        verbose_name='Mostrar sugerencias de productos'
    )
 
    onboarding_completado = models.BooleanField(
        default=False,
        verbose_name='Ha visto la guía de bienvenida'
    )

    # Lista
    confirmar_vaciar_lista = models.BooleanField(
        default=True,
        verbose_name='Pedir confirmación antes de vaciar la lista'
    )
    agrupar_por_pasillos = models.BooleanField(
        default=True,
        verbose_name='Agrupar productos por pasillos'
    )
    marcar_done_al_tocar = models.BooleanField(
        default=False,
        verbose_name='Marcar producto como cogido con un solo toque'
    )

    # Notificaciones
    recordatorio_semanal = models.BooleanField(
        default=False,
        verbose_name='Recordatorio semanal de la compra'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Preferencia de usuario'
        verbose_name_plural = 'Preferencias de usuarios'

    def __str__(self):
        return f"Preferencias de {self.usuario.username}"