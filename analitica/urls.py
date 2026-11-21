from django.urls import path

from . import views

app_name = 'analitica'

urlpatterns = [
    path('panel/analitica/', views.DashboardView.as_view(), name='dashboard'),
]