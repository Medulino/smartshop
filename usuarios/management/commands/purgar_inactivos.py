from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from usuarios.models import Usuario


class Command(BaseCommand):
    help = ('Borra cuentas que nunca se activaron (is_active=False) y que llevan '
            'más de --dias días registradas.')

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias', type=int, default=7,
            help='Antigüedad mínima en días para borrar (por defecto 7)',
        )

    def handle(self, *args, **options):
        limite = timezone.now() - timedelta(days=options['dias'])
        qs = Usuario.objects.filter(is_active=False, date_joined__lt=limite)
        total = qs.count()
        qs.delete()
        self.stdout.write(self.style.SUCCESS(
            f'Cuentas inactivas eliminadas: {total}'
        ))
