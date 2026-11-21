from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class InstitucionContextMixin(LoginRequiredMixin):
    """Resuelve la institución del usuario autenticado y la deja en self.institucion."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        institucion = getattr(request.user, 'institucion', None)
        if not institucion or not institucion.activa:
            messages.error(request, "Tu usuario no pertenece a una institución activa.")
            raise PermissionDenied("Sin institución activa.")

        self.institucion = institucion
        return super().dispatch(request, *args, **kwargs)


class InstitucionScopedMixin(InstitucionContextMixin):
    """Filtra el queryset por la institución del usuario (aislamiento multi-tenant)."""
    # Sobrescribir si la relación no es directa. Ej: 'proyecto__institucion'
    institucion_lookup_field = 'institucion'

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(**{self.institucion_lookup_field: self.institucion})


class InstitucionFormMixin:
    """Asigna automáticamente la institución al guardar un formulario de creación."""

    def form_valid(self, form):
        if hasattr(form.instance, 'institucion_id') and not form.instance.institucion_id:
            form.instance.institucion = self.institucion
        return super().form_valid(form)