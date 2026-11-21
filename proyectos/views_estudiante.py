import logging
from django.conf import settings
from django.contrib import messages
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import DetailView, FormView, ListView

from usuarios.mixins import EstudianteRequiredMixin

from .forms import EntregaForm
from .models import Entrega, Hito, Proyecto
from .services import ESTADOS_ENTREGABLES, EntregaNoPermitida, puede_entregar, registrar_entrega

logger = logging.getLogger(__name__)


class MisProyectosMixin(EstudianteRequiredMixin):
    def proyectos_del_estudiante(self):
        return Proyecto.objects.filter(institucion=self.institucion, estudiante=self.request.user)


class MisProyectosListView(MisProyectosMixin, ListView):
    template_name = 'estudiante/proyecto_list.html'
    context_object_name = 'proyectos'

    def get_queryset(self):
        return (
            self.proyectos_del_estudiante()
            .select_related('asesor', 'periodo', 'carrera')
            .order_by('-creado_en')
        )


class MiProyectoDetailView(MisProyectosMixin, DetailView):
    template_name = 'estudiante/proyecto_detail.html'
    context_object_name = 'proyecto'

    def get_queryset(self):
        return self.proyectos_del_estudiante().select_related('asesor', 'periodo', 'carrera')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        proyecto = self.object
        hoy = timezone.localdate()
        hitos = list(
            proyecto.hitos.prefetch_related(
                Prefetch(
                    'entregas',
                    queryset=Entrega.objects.select_related('subido_por').prefetch_related('revisiones__docente'),
                )
            )
        )
        en_curso = proyecto.estado == Proyecto.Estado.EN_CURSO
        for h in hitos:
            h.entregable = en_curso and h.estado in ESTADOS_ENTREGABLES
            h.vencido = h.fecha_limite < hoy and h.estado != Hito.Estado.APROBADO
        ctx['hitos'] = hitos
        return ctx


class EntregaCreateView(MisProyectosMixin, FormView):
    template_name = 'estudiante/entrega_form.html'
    form_class = EntregaForm

    def get_hito(self):
        if not hasattr(self, '_hito'):
            self._hito = get_object_or_404(
                Hito.objects.select_related('proyecto'),
                pk=self.kwargs['hito_pk'],
                proyecto__institucion=self.institucion,
                proyecto__estudiante=self.request.user,
            )
        return self._hito

    def get_success_url(self):
        return reverse('proyectos:estudiante_proyecto_detail', args=[self.get_hito().proyecto_id])

    def bloqueado(self):
        hito = self.get_hito()
        if puede_entregar(hito):
            return None
        if hito.estado == Hito.Estado.ENTREGADO:
            mensaje = "Este hito ya fue entregado y está pendiente de revisión."
        elif hito.estado == Hito.Estado.APROBADO:
            mensaje = "Este hito ya fue aprobado."
        else:
            mensaje = "El proyecto ya está completado."
        messages.error(self.request, mensaje)
        return redirect(self.get_success_url())

    def get(self, request, *args, **kwargs):
        respuesta = self.bloqueado()
        return respuesta if respuesta is not None else super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        respuesta = self.bloqueado()
        return respuesta if respuesta is not None else super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        hito = self.get_hito()
        ctx['hito'] = hito
        ctx['proyecto'] = hito.proyecto
        ctx['siguiente_version'] = hito.entregas.count() + 1
        ctx['settings_max_mb'] = settings.MAX_UPLOAD_SIZE_MB
        ctx['url_cancelar'] = self.get_success_url()
        return ctx

    def form_valid(self, form):
        try:
            entrega = registrar_entrega(
                hito=self.get_hito(),
                usuario=self.request.user,
                archivo=form.cleaned_data['archivo'],
                comentario=form.cleaned_data['comentario'],
            )
        except EntregaNoPermitida as e:
            messages.error(self.request, str(e))
            return redirect(self.get_success_url())
        except Exception:
            logger.exception("Error al registrar la entrega del hito %s", self.get_hito().pk)
            messages.error(self.request, "No se pudo subir el archivo. Inténtalo nuevamente en unos minutos.")
            return self.form_invalid(form)

        messages.success(self.request, f"Entrega v{entrega.version} registrada. Tu asesor será notificado.")
        return redirect(self.get_success_url())