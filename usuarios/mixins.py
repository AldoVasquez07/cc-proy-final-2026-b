from django.contrib import messages
from django.shortcuts import redirect

from core.mixins import InstitucionContextMixin

from . import roles
from .utils import redirigir_2fa


class RolRequiredMixin(InstitucionContextMixin):
    roles_permitidos = ()
    exigir_2fa = True

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if self.exigir_2fa and not request.user.is_verified():
            return redirigir_2fa(request)
        if request.user.rol not in self.roles_permitidos:
            messages.error(request, "No tienes permiso para acceder a esta sección.")
            return redirect('usuarios:home')
        return super().dispatch(request, *args, **kwargs)


class CoordinadorRequiredMixin(RolRequiredMixin):
    roles_permitidos = roles.ROLES_COORDINADOR


class DocenteRequiredMixin(RolRequiredMixin):
    roles_permitidos = roles.ROLES_DOCENTE


class EstudianteRequiredMixin(RolRequiredMixin):
    roles_permitidos = roles.ROLES_ESTUDIANTE


class CoordinadorODocenteRequiredMixin(RolRequiredMixin):
    roles_permitidos = roles.ROLES_COORDINADOR_DOCENTE