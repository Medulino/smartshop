from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from usuarios.models import Usuario


class Command(BaseCommand):
    help = (
        'Concede (o renueva) el plan premium a un usuario. '
        'Sin pasarela de pago por ahora: sirve para la activación manual '
        '(renovación o regalo) mientras no hay cobros automáticos.'
    )

    def add_arguments(self, parser):
        parser.add_argument('email', help='Email del usuario')
        parser.add_argument(
            '--dias', type=int, default=30,
            help='Días de premium a añadir (por defecto 30).',
        )

    def handle(self, *args, **options):
        email = options['email'].strip().lower()
        dias = options['dias']

        if dias <= 0:
            raise CommandError('--dias debe ser mayor que 0.')

        try:
            usuario = Usuario.objects.get(email__iexact=email)
        except Usuario.DoesNotExist:
            raise CommandError(f'No existe ningún usuario con email {email!r}.')

        desde = usuario.premium_hasta if usuario.es_premium else timezone.now()
        usuario.premium_hasta = desde + timedelta(days=dias)
        usuario.save(update_fields=['premium_hasta'])

        self.stdout.write(self.style.SUCCESS(
            f'Premium de {usuario.email} hasta {usuario.premium_hasta:%d/%m/%Y %H:%M}. '
            f'({usuario.dias_premium_restantes} días restantes)'
        ))
