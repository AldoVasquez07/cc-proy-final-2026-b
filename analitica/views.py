from django.views.generic import TemplateView

from usuarios.mixins import CoordinadorODocenteRequiredMixin

from . import services


class DashboardView(CoordinadorODocenteRequiredMixin, TemplateView):
    """Coordinador: global por institución. Docente: solo su cartera."""
    template_name = 'analitica/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        periodos = services.periodos_disponibles(self.institucion)
        periodo_sel = self.request.GET.get('periodo', '')
        if not (periodo_sel.isdigit() and periodos.filter(pk=periodo_sel).exists()):
            periodo_sel = ''

        asesor = self.request.user if self.request.user.es_docente else None
        panel = services.construir_panel(
            institucion=self.institucion, asesor=asesor, periodo_id=periodo_sel or None,
        )
        ctx.update({
            'panel': panel,
            'graficos': services.datos_graficos(panel),
            'periodos': periodos,
            'periodo_sel': periodo_sel,
            'es_global': asesor is None,
        })
        return ctx