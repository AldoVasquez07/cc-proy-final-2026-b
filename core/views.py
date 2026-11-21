from django.contrib import messages
from django.db.models import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from usuarios.mixins import CoordinadorRequiredMixin

from .forms import CarreraForm, PeriodoForm
from .mixins import InstitucionScopedMixin
from .models import Carrera, PeriodoAcademico


class LandingView(TemplateView):
    template_name = 'core/landing.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('usuarios:home')
        return super().dispatch(request, *args, **kwargs)


class GestionMixin(CoordinadorRequiredMixin, InstitucionScopedMixin):
    nombre_singular = ''
    url_lista = ''

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['nombre_singular'] = self.nombre_singular
        ctx['url_cancelar'] = reverse(self.url_lista)
        return ctx


class GestionFormMixin(GestionMixin):
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['institucion'] = self.institucion
        return kwargs

    def get_success_url(self):
        return reverse(self.url_lista)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        accion = 'Editar' if getattr(self, 'object', None) else 'Registrar'
        ctx['titulo'] = f"{accion} {self.nombre_singular}"
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f"{self.nombre_singular} guardado correctamente.")
        return super().form_valid(form)


class GestionDeleteMixin(GestionMixin):
    template_name = 'gestion/confirm_delete.html'

    def get_success_url(self):
        return reverse(self.url_lista)

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, f"No se puede eliminar: el registro está siendo usado por otros datos.")
            return redirect(self.get_success_url())
        messages.success(self.request, f"{self.nombre_singular} eliminado.")
        return response


# ── Carreras ─────────────────────────────────────────────────
class CarreraMixin:
    model = Carrera
    nombre_singular = 'carrera'
    url_lista = 'core:carrera_list'


class CarreraListView(CarreraMixin, GestionMixin, ListView):
    template_name = 'gestion/carrera_list.html'
    context_object_name = 'carreras'

    def get_queryset(self):
        return super().get_queryset().order_by('nombre')


class CarreraCreateView(CarreraMixin, GestionFormMixin, CreateView):
    form_class = CarreraForm
    template_name = 'gestion/form_generic.html'


class CarreraUpdateView(CarreraMixin, GestionFormMixin, UpdateView):
    form_class = CarreraForm
    template_name = 'gestion/form_generic.html'


class CarreraDeleteView(CarreraMixin, GestionDeleteMixin, DeleteView):
    pass


# ── Periodos académicos ──────────────────────────────────────
class PeriodoMixin:
    model = PeriodoAcademico
    nombre_singular = 'periodo académico'
    url_lista = 'core:periodo_list'


class PeriodoListView(PeriodoMixin, GestionMixin, ListView):
    template_name = 'gestion/periodo_list.html'
    context_object_name = 'periodos'

    def get_queryset(self):
        return super().get_queryset().order_by('-fecha_inicio')


class PeriodoCreateView(PeriodoMixin, GestionFormMixin, CreateView):
    form_class = PeriodoForm
    template_name = 'gestion/form_generic.html'


class PeriodoUpdateView(PeriodoMixin, GestionFormMixin, UpdateView):
    form_class = PeriodoForm
    template_name = 'gestion/form_generic.html'


class PeriodoDeleteView(PeriodoMixin, GestionDeleteMixin, DeleteView):
    pass