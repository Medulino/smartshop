from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    path('registro/', views.RegistroView.as_view(), name='registro'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('onboarding/', views.completar_onboarding, name='completar_onboarding'),
]