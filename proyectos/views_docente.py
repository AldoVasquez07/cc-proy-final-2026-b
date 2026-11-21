from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from core.models import PeriodoAcademico
from usuarios.mixins import DocenteRequiredMixin

from .forms import HitoForm
from .models import Hito, Proyecto


class CarteraMixin(DocenteRequiredMixin):
    def proyectos_del_docente(self):
        return Proyecto.objects.filter(institucion=self.institucion, asesor=self.request.user)


class CarteraListView(CarteraMixin, ListView):
    template_name = 'docente/proyecto_list.html'
    context_object_name = 'proyectos'
    paginate_by = 20

    def get_queryset(self):
        qs = (
            self.proyectos_del_docente()
            .select_related('estudiante', 'periodo', 'carrera')
            .annotate(
                total_hitos=Count('hitos'),
                hitos_aprobados=Count('hitos', filter=Q(hitos__estado=Hito.Estado.APROBADO)),
                por_revisar=Count('hitos', filter=Q(hitos__estado=Hito.Estado.ENTREGADO)),
            )
        )
        q = self.request.GET.get('q', '').strip()
        periodo = self.request.GET.get('periodo', '')
        estado = self.request.GET.get('estado', '')
        if q:
            qs = qs.filter(
                Q(titulo__icontains=q) |
                Q(estudiante__first_name__icontains=q) | Q(estudiante__last_name__icontains=q)
            )
        if periodo.isdigit():
            qs = qs.filter(periodo_id=periodo)
        if estado in Proyecto.Estado.values:
            qs = qs.filter(estado=estado)
        return qs.order_by('-creado_en')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        propios = self.proyectos_del_docente()
        ctx['q'] = self.request.GET.get('q', '')
        ctx['periodo_sel'] = self.request.GET.get('periodo', '')
        ctx['estado_sel'] = self.request.GET.get('estado', '')
        ctx['periodos'] = PeriodoAcademico.objects.filter(institucion=self.institucion)
        ctx['estados'] = Proyecto.Estado.choices
        ctx['total_proyectos'] = propios.count()
        ctx['total_por_revisar'] = Hito.objects.filter(
            proyecto__in=propios, estado=Hito.Estado.ENTREGADO,
        ).count()
        return ctx


class CarteraDetailView(CarteraMixin, DetailView):
    template_name = 'docente/proyecto_detail.html'
    context_object_name = 'proyecto'

    def get_queryset(self):
        return self.proyectos_del_docente().select_related('estudiante', 'periodo', 'carrera')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['hitos'] = self.object.hitos.annotate(num_entregas=Count('entregas'))
        return ctx


# ── Hitos ────────────────────────────────────────────────────
class HitoBaseMixin(CarteraMixin):
    def resolver_proyecto(self):
        raise NotImplementedError

    def get_proyecto(self):
        if not hasattr(self, '_proyecto'):
            self._proyecto = self.resolver_proyecto()
        return self._proyecto

    def get_success_url(self):
        return reverse('proyectos:docente_proyecto_detail', args=[self.get_proyecto().pk])

    def bloqueado(self):
        proyecto = self.get_proyecto()
        if proyecto.estado == Proyecto.Estado.COMPLETADO:
            messages.error(self.request, "El proyecto ya está completado: no se pueden modificar sus hitos.")
            return redirect(self.get_success_url())
        return None

    def get(self, request, *args, **kwargs):
        respuesta = self.bloqueado()
        if respuesta is not None:
            return respuesta
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        respuesta = self.bloqueado()
        if respuesta is not None:
            return respuesta
        return super().post(request, *args, **kwargs)


class HitoFormMixin(HitoBaseMixin):
    form_class = HitoForm
    template_name = 'gestion/form_generic.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['proyecto'] = self.get_proyecto()
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        accion = 'Editar' if getattr(self, 'object', None) else 'Nuevo'
        ctx['titulo'] = f"{accion} hito"
        ctx['url_cancelar'] = self.get_success_url()
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Hito guardado correctamente.")
        return super().form_valid(form)


class HitoObjetoMixin:
    def get_queryset(self):
        return Hito.objects.filter(
            proyecto__institucion=self.institucion,
            proyecto__asesor=self.request.user,
        ).select_related('proyecto')

    def resolver_proyecto(self):
        return self.get_object().proyecto


class HitoCreateView(HitoFormMixin, CreateView):
    model = Hito

    def resolver_proyecto(self):
        return get_object_or_404(self.proyectos_del_docente(), pk=self.kwargs['proyecto_pk'])


class HitoUpdateView(HitoObjetoMixin, HitoFormMixin, UpdateView):
    pass


class HitoDeleteView(HitoObjetoMixin, HitoBaseMixin, DeleteView):
    template_name = 'gestion/confirm_delete.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['nombre_singular'] = 'hito'
        ctx['url_cancelar'] = self.get_success_url()
        return ctx

    def form_valid(self, form):
        if self.object.entregas.exists():
            messages.error(self.request, "No se puede eliminar un hito que ya tiene entregas.")
            return redirect(self.get_success_url())
        messages.success(self.request, "Hito eliminado.")
        return super().form_valid(form)