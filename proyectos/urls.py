from django.urls import path

from . import views, views_docente

app_name = 'proyectos'

urlpatterns = [
    # Coordinador
    path('proyectos/', views.ProyectoListView.as_view(), name='proyecto_list'),
    path('proyectos/crear/', views.ProyectoCreateView.as_view(), name='proyecto_create'),
    path('proyectos/<int:pk>/', views.ProyectoDetailView.as_view(), name='proyecto_detail'),
    path('proyectos/<int:pk>/editar/', views.ProyectoUpdateView.as_view(), name='proyecto_update'),
    path('proyectos/<int:pk>/eliminar/', views.ProyectoDeleteView.as_view(), name='proyecto_delete'),

    # Docente asesor
    path('docente/proyectos/', views_docente.CarteraListView.as_view(), name='docente_proyecto_list'),
    path('docente/proyectos/<int:pk>/', views_docente.CarteraDetailView.as_view(), name='docente_proyecto_detail'),
    path('docente/proyectos/<int:proyecto_pk>/hitos/crear/', views_docente.HitoCreateView.as_view(), name='hito_create'),
    path('docente/hitos/<int:pk>/editar/', views_docente.HitoUpdateView.as_view(), name='hito_update'),
    path('docente/hitos/<int:pk>/eliminar/', views_docente.HitoDeleteView.as_view(), name='hito_delete'),
]