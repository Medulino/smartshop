from .models import PreferenciaUsuario, _flags_cache


def flags(request):
    if not request.user.is_authenticated:
        return {
            'flags': {},
            'flags_bloqueados': {},
            'es_premium': False,
            'premium_hasta': None,
        }

    nombres = [
        'plantillas', 'historial', 'productos_favoritos',
        'sugerencias_inteligentes', 'compartir_lista',
        'exportar_pdf', 'estadisticas', 'modo_colaborativo',
        'onboarding', 'configuracion_super', 'supermercados_publicos',
    ]

    # (activo, requiere_premium) por flag, cacheado unos segundos porque se
    # cambian desde el admin. La parte per-usuario (plan) se calcula aquí.
    datos_flags = _flags_cache()

    es_premium = request.user.es_premium
    flags_activos = {}
    flags_bloqueados = {}
    for nombre in nombres:
        estado = datos_flags.get(nombre)
        if not estado:
            flags_activos[nombre] = False
            continue
        activo, requiere_premium = estado
        if not activo:
            flags_activos[nombre] = False
        elif requiere_premium and not es_premium:
            # Feature premium activa, pero el usuario es básico: se muestra
            # como candado (no desaparece) para invitar a hacerse premium.
            flags_activos[nombre] = False
            flags_bloqueados[nombre] = True
        else:
            flags_activos[nombre] = True

    prefs, _ = PreferenciaUsuario.objects.get_or_create(
        usuario=request.user
    )

    return {
        'flags': flags_activos,
        'flags_bloqueados': flags_bloqueados,
        'es_premium': es_premium,
        'premium_hasta': request.user.premium_hasta,
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
