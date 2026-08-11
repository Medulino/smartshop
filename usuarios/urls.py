from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = 'usuarios'

urlpatterns = [
    path('registro/', views.RegistroView.as_view(), name='registro'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('onboarding/', views.completar_onboarding, name='completar_onboarding'),
    path('premium/', views.premium, name='premium'),
    path('plan/', views.plan, name='plan'),
    path('cambiar-password/', auth_views.PasswordChangeView.as_view(
        template_name='usuarios/cambiar_password.html',
        success_url=reverse_lazy('usuarios:cambiar_password_hecho'),
    ), name='cambiar_password'),
    path('cambiar-password/hecho/', auth_views.PasswordChangeDoneView.as_view(
        template_name='usuarios/cambiar_password_hecho.html',
    ), name='cambiar_password_hecho'),
    path('activacion-pendiente/', views.activacion_pendiente, name='activacion_pendiente'),
    path('reenviar-activacion/', views.reenviar_activacion, name='reenviar_activacion'),
    path('activar/<uidb64>/<token>/', views.activar_cuenta, name='activar_cuenta'),
]