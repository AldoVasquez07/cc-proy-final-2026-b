from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('', include('usuarios.urls')),
    path('', include('proyectos.urls')),
    path('', include('analitica.urls')),
]

if settings.DEBUG and not settings.CLOUDINARY_CONFIGURADO:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)