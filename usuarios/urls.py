from django.contrib.auth import views as auth_views
from django.urls import path

from . import views, views_gestion
from .forms import LoginForm

app_name = 'usuarios'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(
        template_name='usuarios/login.html',
        authentication_form=LoginForm,
        redirect_authenticated_user=True,
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('registro/', views.RegistroInstitucionView.as_view(), name='registro'),
    path('panel/', views.HomeView.as_view(), name='home'),
    path('2fa/configurar/', views.Configurar2FAView.as_view(), name='2fa_configurar'),
    path('2fa/verificar/', views.Verificar2FAView.as_view(), name='2fa_verificar'),

    # Gestión de docentes (Coordinador)
    path('gestion/docentes/', views_gestion.DocenteListView.as_view(), name='docente_list'),
    path('gestion/docentes/crear/', views_gestion.DocenteCreateView.as_view(), name='docente_create'),
    path('gestion/docentes/<int:pk>/editar/', views_gestion.DocenteUpdateView.as_view(), name='docente_update'),
    path('gestion/docentes/<int:pk>/estado/', views_gestion.DocenteToggleView.as_view(), name='docente_toggle'),

    # Gestión de estudiantes (Coordinador)
    path('gestion/estudiantes/', views_gestion.EstudianteListView.as_view(), name='estudiante_list'),
    path('gestion/estudiantes/crear/', views_gestion.EstudianteCreateView.as_view(), name='estudiante_create'),
    path('gestion/estudiantes/<int:pk>/editar/', views_gestion.EstudianteUpdateView.as_view(), name='estudiante_update'),
    path('gestion/estudiantes/<int:pk>/estado/', views_gestion.EstudianteToggleView.as_view(), name='estudiante_toggle'),
]