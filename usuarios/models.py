
from django.contrib.auth.models import AbstractUser
from django.db import models


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

    # Login con email en vez de username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['-fecha_registro']

    def __str__(self):
        return f"{self.username} ({self.email})"

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

class FeatureFlag(models.Model):
    """
    Controla qué funcionalidades están activas.
    Se gestiona desde el admin sin tocar código.
    """
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=False)
    solo_superusuarios = models.BooleanField(
        default=False,
        help_text='Si está marcado, solo lo ven los superusuarios aunque esté activo'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Feature Flag'
        verbose_name_plural = 'Feature Flags'
        ordering = ['nombre']

    def __str__(self):
        estado = '✅' if self.activo else '❌'
        return f"{estado} {self.nombre}"

    @classmethod
    def esta_activo(cls, nombre, usuario=None):
        """
        Uso: FeatureFlag.esta_activo('plantillas')
        Devuelve True si la funcionalidad está activa.
        """
        try:
            flag = cls.objects.get(nombre=nombre)
            if not flag.activo:
                return False
            if flag.solo_superusuarios and usuario and not usuario.is_superuser:
                return False
            return True
        except cls.DoesNotExist:
            return False
        

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