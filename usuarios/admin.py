from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, FeatureFlag, PreferenciaUsuario


class PreferenciaInline(admin.StackedInline):
    model = PreferenciaUsuario
    can_delete = False
    verbose_name = 'Preferencias'


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = [
        'username', 'email', 'avatar',
        'fecha_registro', 'activo',
        'total_listas', 'total_productos_añadidos'
    ]
    list_filter = ['activo', 'fecha_registro']
    search_fields = ['username', 'email']
    readonly_fields = ['fecha_registro', 'total_listas', 'total_productos_añadidos']
    inlines = [PreferenciaInline]

    fieldsets = UserAdmin.fieldsets + (
        ('Perfil', {
            'fields': ('avatar', 'activo', 'fecha_registro')
        }),
        ('Estadísticas', {
            'fields': ('total_listas', 'total_productos_añadidos')
        }),
    )


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activo', 'solo_superusuarios', 'descripcion', 'updated_at']
    list_editable = ['activo', 'solo_superusuarios']
    search_fields = ['nombre']


@admin.register(PreferenciaUsuario)
class PreferenciaUsuarioAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'agrupar_por_pasillos', 'confirmar_vaciar_lista', 'recordatorio_semanal']
    search_fields = ['usuario__username']