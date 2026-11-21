from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from django.db.models import Q

from core.models import PeriodoAcademico
from core.views import GestionDeleteMixin, GestionFormMixin, GestionMixin

from .forms import ProyectoForm
from .models import Proyecto


class ProyectoMixin:
    model = Proyecto
    nombre_singular = 'proyecto'
    url_lista = 'proyectos:proyecto_list'


class ProyectoListView(ProyectoMixin, GestionMixin, ListView):
    template_name = 'proyectos/proyecto_list.html'
    context_object_name = 'proyectos'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('estudiante', 'asesor', 'periodo', 'carrera')
        q = self.request.GET.get('q', '').strip()
        periodo = self.request.GET.get('periodo', '')
        estado = self.request.GET.get('estado', '')
        if q:
            qs = qs.filter(
                Q(titulo__icontains=q) |
                Q(estudiante__first_name__icontains=q) | Q(estudiante__last_name__icontains=q) |
                Q(asesor__first_name__icontains=q) | Q(asesor__last_name__icontains=q)
            )
        if periodo.isdigit():
            qs = qs.filter(periodo_id=periodo)
        if estado in Proyecto.Estado.values:
            qs = qs.filter(estado=estado)
        return qs.order_by('-creado_en')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['periodo_sel'] = self.request.GET.get('periodo', '')
        ctx['estado_sel'] = self.request.GET.get('estado', '')
        ctx['periodos'] = PeriodoAcademico.objects.filter(institucion=self.institucion)
        ctx['estados'] = Proyecto.Estado.choices
        return ctx


class ProyectoDetailView(ProyectoMixin, GestionMixin, DetailView):
    template_name = 'proyectos/proyecto_detail.html'
    context_object_name = 'proyecto'

    def get_queryset(self):
        return super().get_queryset().select_related('estudiante', 'asesor', 'periodo', 'carrera')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['hitos'] = self.object.hitos.all()
        return ctx


class ProyectoCreateView(ProyectoMixin, GestionFormMixin, CreateView):
    form_class = ProyectoForm
    template_name = 'gestion/form_generic.html'


class ProyectoUpdateView(ProyectoMixin, GestionFormMixin, UpdateView):
    form_class = ProyectoForm
    template_name = 'gestion/form_generic.html'


class ProyectoDeleteView(ProyectoMixin, GestionDeleteMixin, DeleteView):
    pass