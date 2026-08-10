from django.core.cache import cache

from .models import FeatureFlag, PreferenciaUsuario


_FLAGS_CACHE_KEY = 'feature_flags_v1'
_FLAGS_CACHE_TTL = 60


def flags(request):
    if not request.user.is_authenticated:
        return {'flags': {}, 'prefs': {}}

    nombres = [
        'plantillas', 'historial', 'productos_favoritos',
        'sugerencias_inteligentes', 'compartir_lista',
        'exportar_pdf', 'estadisticas', 'modo_colaborativo',
        'onboarding', 'configuracion_super', 'supermercados_publicos',
    ]

    # Una sola consulta a la BD para todos los flags (antes era una query
    # por flag en cada request), cacheada unos segundos porque se cambian
    # desde el admin.
    datos_flags = cache.get(_FLAGS_CACHE_KEY)
    if datos_flags is None:
        datos_flags = {
            f.nombre: (f.activo, f.solo_superusuarios)
            for f in FeatureFlag.objects.only('nombre', 'activo', 'solo_superusuarios')
        }
        cache.set(_FLAGS_CACHE_KEY, datos_flags, _FLAGS_CACHE_TTL)

    flags_activos = {}
    for nombre in nombres:
        estado = datos_flags.get(nombre)
        if estado and estado[0] and not (estado[1] and not request.user.is_superuser):
            flags_activos[nombre] = True
        else:
            flags_activos[nombre] = False

    prefs, _ = PreferenciaUsuario.objects.get_or_create(
        usuario=request.user
    )

    return {
        'flags': flags_activos,
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