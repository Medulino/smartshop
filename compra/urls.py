from django.urls import path
from . import views

app_name = 'compra'

urlpatterns = [
    path('', views.ListaCompraView.as_view(), name='lista'),
    path('añadir/', views.añadir_producto, name='añadir_producto'),
    path('toggle/<int:item_id>/', views.toggle_en_carro, name='toggle_en_carro'),
    path('eliminar/<int:item_id>/', views.eliminar_producto, name='eliminar_producto'),
    path('vaciar/<int:lista_id>/', views.vaciar_lista, name='vaciar_lista'),
    path('vaciar-marcados/<int:lista_id>/', views.vaciar_marcados, name='vaciar_marcados'),
    path('asignar-pasillo/<int:item_id>/', views.asignar_pasillo, name='asignar_pasillo'),
    path('foto/', views.analizar_foto, name='analizar_foto'),

    # Configuración
    path('configuracion/', views.ConfiguracionView.as_view(), name='configuracion'),
    path('configuracion/pasillo/crear/<int:supermercado_id>/', views.crear_pasillo, name='crear_pasillo'),
    path('configuracion/pasillo/eliminar/<int:pasillo_id>/', views.eliminar_pasillo, name='eliminar_pasillo'),
    path('configuracion/pasillo/reordenar/<int:supermercado_id>/', views.reordenar_pasillos, name='reordenar_pasillos'),
    path('configuracion/keyword/crear/<int:pasillo_id>/', views.crear_keyword, name='crear_keyword'),
    path('configuracion/keyword/eliminar/<int:keyword_id>/', views.eliminar_keyword, name='eliminar_keyword'),

    # Plantillas e historial
    path('plantilla/guardar/<int:lista_id>/', views.guardar_como_plantilla, name='guardar_como_plantilla'),
    path('plantilla/usar/<int:plantilla_id>/', views.usar_plantilla, name='usar_plantilla'),
    path('plantilla/eliminar/<int:plantilla_id>/', views.eliminar_plantilla, name='eliminar_plantilla'),
    path('historial/', views.HistorialView.as_view(), name='historial'),
    path('lista/repetir/<int:lista_id>/', views.repetir_lista, name='repetir_lista'),
    path('lista/pdf/<int:lista_id>/', views.exportar_pdf, name='exportar_pdf'),
    path('archivar/<int:lista_id>/', views.archivar_lista, name='archivar_lista'),
]