from django.urls import path

from . import (
    views, views_constancia, views_cron, views_docente, views_entregas, views_estudiante,
    views_publicacion, views_publico,
)

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
    path('docente/entregas/<int:entrega_pk>/revisar/', views_docente.RevisionCreateView.as_view(), name='revision_create'),

    # Estudiante
    path('estudiante/proyectos/', views_estudiante.MisProyectosListView.as_view(), name='estudiante_proyecto_list'),
    path('estudiante/proyectos/<int:pk>/', views_estudiante.MiProyectoDetailView.as_view(), name='estudiante_proyecto_detail'),
    path('estudiante/hitos/<int:hito_pk>/entregar/', views_estudiante.EntregaCreateView.as_view(), name='entrega_create'),

    # Descarga (coordinador, docente asesor o estudiante dueño)
    path('entregas/<int:pk>/descargar/', views_entregas.DescargarEntregaView.as_view(), name='entrega_descargar'),

    # Constancia (privada) y verificación (pública)
    path('constancias/proyecto/<int:proyecto_pk>/', views_constancia.ConstanciaView.as_view(), name='constancia'),
    path('verificar/<uuid:codigo>/', views_constancia.ConstanciaVerificarView.as_view(), name='constancia_verificar'),

    # Publicación (Coordinador, solo POST)
    path('proyectos/<int:pk>/publicacion/', views_publicacion.PublicarProyectoView.as_view(), name='proyecto_publicar'),

    # Repositorio público (sin login)
    path('repositorio/', views_publico.RepositorioListView.as_view(), name='repositorio_list'),
    path('repositorio/<int:pk>/', views_publico.RepositorioDetailView.as_view(), name='repositorio_detail'),

    # Cron-job.org
    path('cron/alertas/', views_cron.cron_alertas, name='cron_alertas'),
]