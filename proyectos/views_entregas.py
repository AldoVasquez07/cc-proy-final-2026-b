from django.shortcuts import get_object_or_404, redirect
from django.views import View

from usuarios import roles
from usuarios.mixins import RolRequiredMixin

from .models import Entrega


class DescargarEntregaView(RolRequiredMixin, View):
    roles_permitidos = (roles.COORDINADOR, roles.DOCENTE, roles.ESTUDIANTE)

    def get(self, request, pk):
        qs = Entrega.objects.select_related('hito__proyecto').filter(
            hito__proyecto__institucion=self.institucion,
        )
        if request.user.es_docente:
            qs = qs.filter(hito__proyecto__asesor=request.user)
        elif request.user.es_estudiante:
            qs = qs.filter(hito__proyecto__estudiante=request.user)
        entrega = get_object_or_404(qs, pk=pk)
        return redirect(entrega.archivo.url)