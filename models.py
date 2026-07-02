from django.db import models


class Supermercado(models.Model):
    """Representa un supermercado concreto con su propia distribución de pasillos."""
    nombre = models.CharField(max_length=200)
    direccion = models.CharField(max_length=300, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Supermercado'
        verbose_name_plural = 'Supermercados'

    def __str__(self):
        return self.nombre


class Pasillo(models.Model):
    """
    Representa un pasillo físico dentro de un supermercado.
    El campo 'orden' determina el recorrido óptimo.
    """
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
        # Un supermercado no puede tener dos pasillos con el mismo orden
        unique_together = ('supermercado', 'orden')

    def __str__(self):
        return f"{self.supermercado.nombre} → {self.orden}. {self.nombre}"


class Keyword(models.Model):
    """
    Palabras clave que se asocian a un pasillo.
    Cuando el usuario escribe un producto, se busca coincidencia aquí
    para asignarlo automáticamente al pasillo correcto.
    """
    pasillo = models.ForeignKey(
        Pasillo,
        on_delete=models.CASCADE,
        related_name='keywords'
    )
    palabra = models.CharField(max_length=100)

    class Meta:
        verbose_name = 'Palabra clave'
        verbose_name_plural = 'Palabras clave'
        # La misma palabra no puede apuntar dos veces al mismo pasillo
        unique_together = ('pasillo', 'palabra')

    def __str__(self):
        return f"{self.palabra} → {self.pasillo.nombre}"


class Lista(models.Model):
    """
    Cabecera de una lista de la compra.
    Cada lista pertenece a un supermercado y tiene una fecha.
    """
    supermercado = models.ForeignKey(
        Supermercado,
        on_delete=models.CASCADE,
        related_name='listas'
    )
    fecha = models.DateField(auto_now_add=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Lista'
        verbose_name_plural = 'Listas'

    def __str__(self):
        return f"Lista {self.supermercado.nombre} - {self.fecha}"

    def total_productos(self):
        """Devuelve el número total de productos en la lista."""
        return self.items.count()

    def productos_en_carro(self):
        """Devuelve cuántos productos ya están en el carro."""
        return self.items.filter(en_carro=True).count()

    def productos_pendientes(self):
        """Devuelve cuántos productos faltan por coger."""
        return self.items.filter(en_carro=False).count()


class ListaItem(models.Model):
    """
    Un producto concreto dentro de una lista de la compra.
    Se relaciona con un pasillo para ordenar el recorrido.
    """
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
        # Los productos se ordenan por el orden del pasillo,
        # y los sin pasillo asignado van al final (nulls_last)
        ordering = [
            models.F('pasillo__orden').asc(nulls_last=True),
            'nombre'
        ]
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'

    def __str__(self):
        pasillo_nombre = self.pasillo.nombre if self.pasillo else 'Sin asignar'
        return f"{self.nombre} ({pasillo_nombre})"
