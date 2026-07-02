from .models import FeatureFlag, PreferenciaUsuario


def flags(request):
    if not request.user.is_authenticated:
        return {'flags': {}, 'prefs': {}}

    nombres = [
        'plantillas', 'historial', 'productos_favoritos',
        'sugerencias_inteligentes', 'compartir_lista',
        'exportar_pdf', 'estadisticas', 'modo_colaborativo',
        'onboarding', 'configuracion_super',
    ]

    prefs, _ = PreferenciaUsuario.objects.get_or_create(
        usuario=request.user
    )

    return {
        'flags': {
            nombre: FeatureFlag.esta_activo(nombre, request.user)
            for nombre in nombres
        },
        'prefs': {
            'mostrar_estadisticas': prefs.mostrar_estadisticas,
            'mostrar_sugerencias': prefs.mostrar_sugerencias,
            'confirmar_vaciar_lista': prefs.confirmar_vaciar_lista,
            'agrupar_por_pasillos': prefs.agrupar_por_pasillos,
            'marcar_done_al_tocar': prefs.marcar_done_al_tocar,
            'recordatorio_semanal': prefs.recordatorio_semanal,
            'onboarding_completado': prefs.onboarding_completado,
        }
    }