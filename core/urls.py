from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.LandingView.as_view(), name='landing'),

    path('gestion/carreras/', views.CarreraListView.as_view(), name='carrera_list'),
    path('gestion/carreras/crear/', views.CarreraCreateView.as_view(), name='carrera_create'),
    path('gestion/carreras/<int:pk>/editar/', views.CarreraUpdateView.as_view(), name='carrera_update'),
    path('gestion/carreras/<int:pk>/eliminar/', views.CarreraDeleteView.as_view(), name='carrera_delete'),

    path('gestion/periodos/', views.PeriodoListView.as_view(), name='periodo_list'),
    path('gestion/periodos/crear/', views.PeriodoCreateView.as_view(), name='periodo_create'),
    path('gestion/periodos/<int:pk>/editar/', views.PeriodoUpdateView.as_view(), name='periodo_update'),
    path('gestion/periodos/<int:pk>/eliminar/', views.PeriodoDeleteView.as_view(), name='periodo_delete'),
]