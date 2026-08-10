from django.db import models
from django.conf import settings
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver

from .cache_pasillos import invalidar_candidatos, invalidar_candidatos_global


class Supermercado(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='supermercados'
    )
    nombre = models.CharField(max_length=200)
    direccion = models.CharField(max_length=300, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    publico = models.BooleanField(
        default=False,
        help_text='Si está marcado, cualquier usuario puede verlo en "Explorar" y copiarlo a su cuenta'
    )
    fecha_publicacion = models.DateTimeField(null=True, blank=True)
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='supermercados_gustados',
        blank=True
    )

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Supermercado'
        verbose_name_plural = 'Supermercados'
        # Un usuario no puede tener dos supermercados con el mismo nombre
        unique_together = ('usuario', 'nombre')

    def __str__(self):
        return f"{self.nombre} ({self.usuario.username})"

    def total_likes(self):
        return self.likes.count()

    def total_pasillos(self):
        return self.pasillos.count()


class Categoria(models.Model):
    """
    Categoría global de producto (p.ej. "Panadería", "Carnicería"),
    independiente de cualquier supermercado. Un Pasillo se "etiqueta"
    con una o varias categorías y hereda de golpe todas sus keywords,
    para que un supermercado nuevo no tenga que empezar casi sin nada.
    """
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'

    def __str__(self):
        return self.nombre


class CategoriaKeyword(models.Model):
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.CASCADE,
        related_name='keywords'
    )
    palabra = models.CharField(max_length=100)

    class Meta:
        ordering = ['palabra']
        verbose_name = 'Palabra clave de categoría'
        verbose_name_plural = 'Palabras clave de categoría'
        unique_together = ('categoria', 'palabra')

    def __str__(self):
        return f"{self.palabra} → {self.categoria.nombre}"


class Pasillo(models.Model):
    supermercado = models.ForeignKey(
        Supermercado,
        on_delete=models.CASCADE,
        related_name='pasillos'
    )
    nombre = models.CharField(max_length=200)
    orden = models.PositiveIntegerField(default=1)
    categorias = models.ManyToManyField(
        Categoria,
        related_name='pasillos',
        blank=True
    )

    class Meta:
        ordering = ['orden']
        verbose_name = 'Pasillo'
        verbose_name_plural = 'Pasillos'
        unique_together = ('supermercado', 'orden')

    def __str__(self):
        return f"{self.supermercado.nombre} → {self.orden}. {self.nombre}"


class Keyword(models.Model):
    pasillo = models.ForeignKey(
        Pasillo,
        on_delete=models.CASCADE,
        related_name='keywords'
    )
    palabra = models.CharField(max_length=100)

    class Meta:
        ordering = ['palabra']
        verbose_name = 'Palabra clave'
        verbose_name_plural = 'Palabras clave'
        unique_together = ('pasillo', 'palabra')

    def __str__(self):
        return f"{self.palabra} → {self.pasillo.nombre}"


class Lista(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='listas'
    )
    supermercado = models.ForeignKey(
        Supermercado,
        on_delete=models.CASCADE,
        related_name='listas'
    )
    fecha = models.DateField(auto_now_add=True)
    activa = models.BooleanField(default=True)
    es_plantilla = models.BooleanField(default=False)
    nombre_plantilla = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Lista'
        verbose_name_plural = 'Listas'
        indexes = [
            models.Index(fields=['usuario', '-fecha'], name='lista_usuario_fecha_idx'),
        ]

    def __str__(self):
        return f"{self.usuario.username} - {self.supermercado.nombre} - {self.fecha}"

    def total_productos(self):
        return self.items.count()

    def productos_en_carro(self):
        return self.items.filter(en_carro=True).count()

    def productos_pendientes(self):
        return self.items.filter(en_carro=False).count()


class ListaItem(models.Model):
    lista = models.ForeignKey(
        Lista,
        on_delete=models.CASCADE,
        related_name='items'
    )
    nombre = models.CharField(max_length=200)
    pasillo = models.ForeignKey(
        Pasillo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items'
    )
    en_carro = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = [
            models.F('pasillo__orden').asc(nulls_last=True),
            'nombre'
        ]
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'

    def __str__(self):
        pasillo_nombre = self.pasillo.nombre if self.pasillo else 'Sin asignar'
        return f"{self.nombre} ({pasillo_nombre})"


# Invalidación de la caché de candidatos de pasillos cuando cambia el
# corpus de palabras (keywords propias, categorías heredadas o pasillos).


@receiver([post_save, post_delete], sender=Keyword)
def _keyword_cambiado(sender, instance, **kwargs):
    invalidar_candidatos(instance.pasillo.supermercado)


@receiver([post_save, post_delete], sender=Pasillo)
def _pasillo_cambiado(sender, instance, **kwargs):
    invalidar_candidatos(instance.supermercado)


@receiver(m2m_changed, sender=Pasillo.categorias.through)
def _categorias_pasillo_cambiadas(sender, instance, **kwargs):
    if kwargs.get('action') in ('post_add', 'post_remove', 'post_clear'):
        invalidar_candidatos(instance.supermercado)


@receiver([post_save, post_delete], sender=CategoriaKeyword)
def _categoria_keyword_cambiada(sender, instance, **kwargs):
    invalidar_candidatos_global()