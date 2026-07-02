from django.urls import path
from . import views

app_name = 'compra'

urlpatterns = [
    # Vista principal
    path('', views.ListaCompraView.as_view(), name='lista'),

    # API endpoints (llamadas AJAX desde el navegador)
    path('añadir/', views.añadir_producto, name='añadir_producto'),
    path('toggle/<int:item_id>/', views.toggle_en_carro, name='toggle_en_carro'),
    path('eliminar/<int:item_id>/', views.eliminar_producto, name='eliminar_producto'),
    path('vaciar/<int:lista_id>/', views.vaciar_lista, name='vaciar_lista'),
    path('vaciar-marcados/<int:lista_id>/', views.vaciar_marcados, name='vaciar_marcados'),
]
