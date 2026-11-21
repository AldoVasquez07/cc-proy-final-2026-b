"""Consultas agregadas del panel analítico. Todo se filtra por institución y, para el docente, por asesor."""
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from core.models import PeriodoAcademico
from proyectos.models import Hito, Proyecto, Revision

PENDIENTES = (Hito.Estado.PENDIENTE, Hito.Estado.OBSERVADO)


def _proyectos(institucion, asesor=None, periodo_id=None):
    qs = Proyecto.objects.filter(institucion=institucion)
    if asesor is not None:
        qs = qs.filter(asesor=asesor)
    if periodo_id:
        qs = qs.filter(periodo_id=periodo_id)
    return qs


def periodos_disponibles(institucion):
    return PeriodoAcademico.objects.filter(institucion=institucion).order_by('-fecha_inicio')


def _pct(parte, total):
    return round(parte * 100 / total, 1) if total else 0


def construir_panel(*, institucion, asesor=None, periodo_id=None, dias_proximos=14):
    """asesor=None → vista global del Coordinador; asesor=<Usuario> → cartera del Docente."""
    proyectos = _proyectos(institucion, asesor, periodo_id)
    hitos = Hito.objects.filter(proyecto__in=proyectos)
    hoy = timezone.localdate()

    # Hitos por estado y tasa de aprobación
    por_estado = {e: 0 for e in Hito.Estado.values}
    for fila in hitos.values('estado').annotate(n=Count('id')):
        por_estado[fila['estado']] = fila['n']
    total_hitos = sum(por_estado.values())

    revisiones = Revision.objects.filter(entrega__hito__proyecto__in=proyectos)
    total_rev = revisiones.count()
    rev_aprobadas = revisiones.filter(aprobada=True).count()

    # Proyectos por estado
    proy_estado = {e: 0 for e in Proyecto.Estado.values}
    for fila in proyectos.values('estado').annotate(n=Count('id')):
        proy_estado[fila['estado']] = fila['n']

    pendientes_qs = hitos.filter(estado__in=PENDIENTES)
    base_filas = pendientes_qs.select_related('proyecto__estudiante')

    # Carga por asesor (solo útil en la vista global)
    carga = []
    if asesor is None:
        filas = (
            proyectos.values('asesor_id', 'asesor__first_name', 'asesor__last_name', 'asesor__username')
            .annotate(
                n_proyectos=Count('id', distinct=True),
                por_revisar=Count('hitos', filter=Q(hitos__estado=Hito.Estado.ENTREGADO)),
            ).order_by('-por_revisar', '-n_proyectos')
        )
        for f in filas:
            nombre = f"{f['asesor__first_name']} {f['asesor__last_name']}".strip() or f['asesor__username']
            carga.append({'asesor': nombre, 'proyectos': f['n_proyectos'], 'por_revisar': f['por_revisar']})

    return {
        'total_proyectos': sum(proy_estado.values()),
        'total_hitos': total_hitos,
        'hitos_por_estado': por_estado,
        'proyectos_por_estado': proy_estado,
        'tasa_hitos_aprobados': _pct(por_estado[Hito.Estado.APROBADO], total_hitos),
        'tasa_revisiones_aprobadas': _pct(rev_aprobadas, total_rev),
        'total_revisiones': total_rev,
        'entregables_pendientes': pendientes_qs.count(),
        'por_revisar': por_estado[Hito.Estado.ENTREGADO],
        'vencidos': list(base_filas.filter(fecha_limite__lt=hoy).order_by('fecha_limite')[:10]),
        'total_vencidos': pendientes_qs.filter(fecha_limite__lt=hoy).count(),
        'proximos': list(
            base_filas.filter(fecha_limite__gte=hoy, fecha_limite__lte=hoy + timedelta(days=dias_proximos))
            .order_by('fecha_limite')[:10]
        ),
        'dias_proximos': dias_proximos,
        'carga_asesores': carga,
    }


def datos_graficos(panel):
    """Estructura serializable para json_script (Chart.js)."""
    etiquetas_hito = dict(Hito.Estado.choices)
    etiquetas_proy = dict(Proyecto.Estado.choices)
    return {
        'hitos': {
            'labels': [etiquetas_hito[k] for k in panel['hitos_por_estado']],
            'data': list(panel['hitos_por_estado'].values()),
        },
        'proyectos': {
            'labels': [etiquetas_proy[k] for k in panel['proyectos_por_estado']],
            'data': list(panel['proyectos_por_estado'].values()),
        },
        'carga': {
            'labels': [c['asesor'] for c in panel['carga_asesores']],
            'proyectos': [c['proyectos'] for c in panel['carga_asesores']],
            'por_revisar': [c['por_revisar'] for c in panel['carga_asesores']],
        },
    }