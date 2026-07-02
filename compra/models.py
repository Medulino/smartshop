from django.db import models
from django.conf import settings


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

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Supermercado'
        verbose_name_plural = 'Supermercados'
        # Un usuario no puede tener dos supermercados con el mismo nombre
        unique_together = ('usuario', 'nombre')

    def __str__(self):
        return f"{self.nombre} ({self.usuario.username})"


class Pasillo(models.Model):
    supermercado = models.ForeignKey(
        Supermercado,
        on_delete=models.CASCADE,
        related_name='pasillos'
    )
    nombre = models.CharField(max_length=200)
    orden = models.PositiveIntegerField(default=1)

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