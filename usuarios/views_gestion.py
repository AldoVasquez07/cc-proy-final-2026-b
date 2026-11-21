from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView
from django.views.generic.detail import SingleObjectMixin

from core.mixins import InstitucionScopedMixin

from . import roles
from .forms import UsuarioGestionForm
from .mixins import CoordinadorRequiredMixin
from .models import Usuario


class UsuarioGestionMixin(CoordinadorRequiredMixin, InstitucionScopedMixin):
    model = Usuario
    rol = None
    rol_singular = ''
    rol_plural = ''
    url_lista = ''
    url_crear = ''
    url_editar = ''
    url_toggle = ''

    def get_queryset(self):
        return super().get_queryset().filter(rol=self.rol).select_related('carrera')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            rol_singular=self.rol_singular,
            rol_plural=self.rol_plural,
            url_lista=self.url_lista,
            url_crear=self.url_crear,
            url_editar=self.url_editar,
            url_toggle=self.url_toggle,
            url_cancelar=reverse(self.url_lista),
        )
        return ctx


class DocenteMixin:
    rol = roles.DOCENTE
    rol_singular = 'docente'
    rol_plural = 'Docentes asesores'
    url_lista = 'usuarios:docente_list'
    url_crear = 'usuarios:docente_create'
    url_editar = 'usuarios:docente_update'
    url_toggle = 'usuarios:docente_toggle'


class EstudianteMixin:
    rol = roles.ESTUDIANTE
    rol_singular = 'estudiante'
    rol_plural = 'Estudiantes'
    url_lista = 'usuarios:estudiante_list'
    url_crear = 'usuarios:estudiante_create'
    url_editar = 'usuarios:estudiante_update'
    url_toggle = 'usuarios:estudiante_toggle'


class UsuarioListView(UsuarioGestionMixin, ListView):
    template_name = 'gestion/usuario_list.html'
    context_object_name = 'usuarios'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q) | Q(last_name__icontains=q) |
                Q(username__icontains=q) | Q(email__icontains=q) | Q(codigo__icontains=q)
            )
        return qs.order_by('last_name', 'first_name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class UsuarioFormMixin(UsuarioGestionMixin):
    form_class = UsuarioGestionForm
    template_name = 'gestion/form_generic.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(institucion=self.institucion, rol=self.rol)
        return kwargs

    def get_success_url(self):
        return reverse(self.url_lista)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        accion = 'Editar' if getattr(self, 'object', None) else 'Registrar'
        ctx['titulo'] = f"{accion} {self.rol_singular}"
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f"{self.rol_singular.capitalize()} guardado correctamente.")
        return super().form_valid(form)


class UsuarioCreateView(UsuarioFormMixin, CreateView):
    pass


class UsuarioUpdateView(UsuarioFormMixin, UpdateView):
    pass


class UsuarioToggleView(UsuarioGestionMixin, SingleObjectMixin, View):
    def post(self, request, *args, **kwargs):
        usuario = self.get_object()
        usuario.is_active = not usuario.is_active
        usuario.save(update_fields=['is_active'])
        estado = 'activado' if usuario.is_active else 'desactivado'
        messages.success(request, f"Usuario {estado}.")
        return redirect(self.url_lista)


# ── Docentes ─────────────────────────────────────────────────
class DocenteListView(DocenteMixin, UsuarioListView):
    pass


class DocenteCreateView(DocenteMixin, UsuarioCreateView):
    pass


class DocenteUpdateView(DocenteMixin, UsuarioUpdateView):
    pass


class DocenteToggleView(DocenteMixin, UsuarioToggleView):
    pass


# ── Estudiantes ──────────────────────────────────────────────
class EstudianteListView(EstudianteMixin, UsuarioListView):
    pass


class EstudianteCreateView(EstudianteMixin, UsuarioCreateView):
    pass


class EstudianteUpdateView(EstudianteMixin, UsuarioUpdateView):
    pass


class EstudianteToggleView(EstudianteMixin, UsuarioToggleView):
    pass