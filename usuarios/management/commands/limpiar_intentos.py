from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from usuarios.models import IntentoFallo


class Command(BaseCommand):
    help = 'Borra los contadores de intentos fallidos que hayan superado la ventana de 24 horas.'

    def handle(self, *args, **options):
        corte = timezone.now() - timedelta(hours=24)
        borrados, _ = IntentoFallo.objects.filter(
            ultimo_intento__lt=corte
        ).delete()
        self.stdout.write(self.style.SUCCESS(f'Intentos antiguos limpiados: {borrados}'))
