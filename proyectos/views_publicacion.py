from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from usuarios.mixins import CoordinadorRequiredMixin

from .forms import PublicacionForm
from .models import Proyecto
from .services import PublicacionNoPermitida, despublicar_proyecto, publicar_proyecto


class PublicarProyectoView(CoordinadorRequiredMixin, View):
    """Solo POST. Acciones: 'publicar' (guarda resumen) y 'despublicar'."""
    http_method_names = ['post']

    def post(self, request, pk):
        proyecto = get_object_or_404(Proyecto, pk=pk, institucion=self.institucion)
        destino = redirect('proyectos:proyecto_detail', pk=proyecto.pk)

        if request.POST.get('accion') == 'despublicar':
            despublicar_proyecto(proyecto=proyecto)
            messages.success(request, "El proyecto ya no es visible en el repositorio público.")
            return destino

        form = PublicacionForm(request.POST)
        if not form.is_valid():
            for errores in form.errors.values():
                for e in errores:
                    messages.error(request, e)
            return destino
        try:
            publicar_proyecto(proyecto=proyecto, resumen=form.cleaned_data['resumen_publico'])
        except PublicacionNoPermitida as e:
            messages.error(request, str(e))
            return destino
        messages.success(request, "Proyecto publicado en el repositorio público.")
        return destino