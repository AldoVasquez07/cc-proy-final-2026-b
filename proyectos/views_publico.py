from urllib.parse import urlencode

from django.db.models import Q
from django.views.generic import DetailView, ListView

from core.models import Institucion

from .models import Proyecto


def proyectos_publicos():
    """Único punto de acceso: solo proyectos completados, publicados y de instituciones activas."""
    return Proyecto.objects.filter(
        publicado=True, estado=Proyecto.Estado.COMPLETADO, institucion__activa=True,
    ).select_related('institucion', 'carrera', 'periodo', 'estudiante', 'asesor', 'constancia')


class RepositorioListView(ListView):
    template_name = 'repositorio/lista.html'
    context_object_name = 'proyectos'
    paginate_by = 12

    def get_queryset(self):
        qs = proyectos_publicos()
        g = self.request.GET
        q = g.get('q', '').strip()[:100]
        if q:
            qs = qs.filter(Q(titulo__icontains=q) | Q(resumen_publico__icontains=q))
        if g.get('institucion'):
            qs = qs.filter(institucion__slug=g['institucion'])
        if g.get('carrera'):
            qs = qs.filter(carrera__nombre=g['carrera'])
        if g.get('periodo'):
            qs = qs.filter(periodo__nombre=g['periodo'])
        if g.get('anio', '').isdigit():
            qs = qs.filter(fecha_publicacion__year=int(g['anio']))
        return qs.order_by('-fecha_publicacion', '-pk')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = proyectos_publicos()
        g = self.request.GET
        ctx['instituciones'] = Institucion.objects.filter(
            pk__in=base.values('institucion_id'),
        ).order_by('nombre')
        ctx['carreras'] = base.exclude(carrera__isnull=True).values_list(
            'carrera__nombre', flat=True).distinct().order_by('carrera__nombre')
        ctx['periodos'] = base.values_list('periodo__nombre', flat=True).distinct().order_by('-periodo__nombre')
        ctx['anios'] = [d.year for d in base.datetimes('fecha_publicacion', 'year', order='DESC')]
        ctx['sel'] = {k: g.get(k, '') for k in ('q', 'institucion', 'carrera', 'periodo', 'anio')}
        ctx['querystring'] = urlencode({k: v for k, v in ctx['sel'].items() if v})
        return ctx


class RepositorioDetailView(DetailView):
    template_name = 'repositorio/detalle.html'
    context_object_name = 'proyecto'

    def get_queryset(self):
        return proyectos_publicos()