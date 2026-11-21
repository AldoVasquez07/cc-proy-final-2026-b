from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, UpdateView

from core.models import PeriodoAcademico
from usuarios.mixins import DocenteRequiredMixin

from .forms import HitoForm, RevisionForm
from .models import Entrega, Hito, Proyecto
from .services import RevisionNoPermitida, registrar_revision, verificar_cierre


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
        ctx['hitos'] = (
            self.object.hitos
            .annotate(num_entregas=Count('entregas'))
            .prefetch_related('entregas')
        )
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
        proyecto = self.object.proyecto
        response = super().form_valid(form)
        verificar_cierre(proyecto)
        messages.success(self.request, "Hito eliminado.")
        return response


# ── Revisión de entregas ─────────────────────────────────────
class RevisionCreateView(CarteraMixin, FormView):
    template_name = 'docente/revision_form.html'
    form_class = RevisionForm

    def get_entrega(self):
        if not hasattr(self, '_entrega'):
            self._entrega = get_object_or_404(
                Entrega.objects.select_related('hito__proyecto__estudiante'),
                pk=self.kwargs['entrega_pk'],
                hito__proyecto__institucion=self.institucion,
                hito__proyecto__asesor=self.request.user,
            )
        return self._entrega

    def get_success_url(self):
        return reverse('proyectos:docente_proyecto_detail', args=[self.get_entrega().hito.proyecto_id])

    def bloqueado(self):
        entrega = self.get_entrega()
        hito = entrega.hito
        mensaje = None
        if hito.proyecto.estado != Proyecto.Estado.EN_CURSO:
            mensaje = "El proyecto ya está completado."
        elif hito.estado != Hito.Estado.ENTREGADO:
            mensaje = "Este hito no está pendiente de revisión."
        elif hito.entregas.first().pk != entrega.pk:
            mensaje = "Existe una versión más reciente de esta entrega."
        if mensaje:
            messages.error(self.request, mensaje)
            return redirect(self.get_success_url())
        return None

    def get(self, request, *args, **kwargs):
        respuesta = self.bloqueado()
        return respuesta if respuesta is not None else super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        respuesta = self.bloqueado()
        return respuesta if respuesta is not None else super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        entrega = self.get_entrega()
        ctx['entrega'] = entrega
        ctx['hito'] = entrega.hito
        ctx['proyecto'] = entrega.hito.proyecto
        ctx['historial'] = entrega.hito.entregas.prefetch_related('revisiones__docente')
        ctx['url_cancelar'] = self.get_success_url()
        return ctx

    def form_valid(self, form):
        entrega = self.get_entrega()
        aprobada = form.cleaned_data['decision'] == 'APROBAR'
        try:
            registrar_revision(
                entrega=entrega,
                docente=self.request.user,
                observacion=form.cleaned_data['observacion'],
                calificacion=form.cleaned_data['calificacion'],
                aprobada=aprobada,
            )
        except RevisionNoPermitida as e:
            messages.error(self.request, str(e))
            return redirect(self.get_success_url())

        proyecto = entrega.hito.proyecto
        proyecto.refresh_from_db(fields=['estado'])
        if proyecto.estado == Proyecto.Estado.COMPLETADO:
            messages.success(self.request, "Hito aprobado. ¡Todos los hitos están aprobados: el proyecto quedó completado y se emitió la constancia!")
        elif aprobada:
            messages.success(self.request, "Hito aprobado.")
        else:
            messages.success(self.request, "Observaciones enviadas al estudiante.")
        return redirect(self.get_success_url())