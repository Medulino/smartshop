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
        'plan', 'premium_hasta',
        'fecha_registro', 'activo',
        'total_listas', 'total_productos_añadidos'
    ]
    list_filter = ['activo', 'fecha_registro']
    search_fields = ['username', 'email']
    readonly_fields = ['fecha_registro', 'total_listas', 'total_productos_añadidos', 'plan']
    inlines = [PreferenciaInline]

    fieldsets = UserAdmin.fieldsets + (
        ('Perfil', {
            'fields': ('avatar', 'activo', 'fecha_registro')
        }),
        ('Plan', {
            'fields': ('premium_hasta', 'plan'),
            'description': 'El plan se deriva de "Premium hasta". '
                           'El superusuario no tiene ventajas: también se le aplica su plan.',
        }),
        ('Estadísticas', {
            'fields': ('total_listas', 'total_productos_añadidos')
        }),
    )

    @admin.display(description='Plan', boolean=True)
    def plan(self, obj):
        return obj.es_premium


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activo', 'requiere_premium', 'descripcion', 'updated_at']
    list_editable = ['activo', 'requiere_premium']
    search_fields = ['nombre']


@admin.register(PreferenciaUsuario)
class PreferenciaUsuarioAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'agrupar_por_pasillos', 'confirmar_vaciar_lista', 'recordatorio_semanal']
    search_fields = ['usuario__username']