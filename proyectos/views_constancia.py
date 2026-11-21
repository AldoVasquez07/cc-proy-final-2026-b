from urllib.parse import quote

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import TemplateView

from usuarios import roles
from usuarios.mixins import RolRequiredMixin

from .models import Constancia

RELACIONES = (
    'proyecto__estudiante', 'proyecto__asesor', 'proyecto__periodo',
    'proyecto__carrera', 'proyecto__institucion',
)


class ConstanciaView(RolRequiredMixin, TemplateView):
    roles_permitidos = (roles.COORDINADOR, roles.DOCENTE, roles.ESTUDIANTE)
    template_name = 'proyectos/constancia.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = Constancia.objects.select_related(*RELACIONES).filter(
            proyecto__institucion=self.institucion,
        )
        user = self.request.user
        if user.es_docente:
            qs = qs.filter(proyecto__asesor=user)
        elif user.es_estudiante:
            qs = qs.filter(proyecto__estudiante=user)
        constancia = get_object_or_404(qs, proyecto_id=self.kwargs['proyecto_pk'])

        url_verificacion = settings.SITE_URL.rstrip('/') + reverse(
            'proyectos:constancia_verificar', args=[constancia.codigo],
        )
        ctx['constancia'] = constancia
        ctx['proyecto'] = constancia.proyecto
        ctx['url_verificacion'] = url_verificacion
        ctx['qr_url'] = f"{settings.QUICKCHART_QR_URL}?text={quote(url_verificacion, safe='')}&size=180&margin=1"
        return ctx


class ConstanciaVerificarView(TemplateView):
    """Vista pública: valida la autenticidad de una constancia por su código."""
    template_name = 'proyectos/constancia_verificar.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['constancia'] = (
            Constancia.objects.select_related(*RELACIONES)
            .filter(codigo=self.kwargs['codigo'])
            .first()
        )
        return ctx

    def render_to_response(self, context, **response_kwargs):
        if context['constancia'] is None:
            response_kwargs['status'] = 404
        return super().render_to_response(context, **response_kwargs)