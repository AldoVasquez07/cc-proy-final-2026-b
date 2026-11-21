from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from . import notificaciones
from .models import Constancia, Entrega, Hito, Proyecto, Revision

ESTADOS_ENTREGABLES = (Hito.Estado.PENDIENTE, Hito.Estado.OBSERVADO)


class EntregaNoPermitida(Exception):
    pass


class RevisionNoPermitida(Exception):
    pass


class PublicacionNoPermitida(Exception):
    pass


def puede_entregar(hito):
    return (
        hito.proyecto.estado == Proyecto.Estado.EN_CURSO
        and hito.estado in ESTADOS_ENTREGABLES
    )


@transaction.atomic
def registrar_entrega(*, hito, usuario, archivo, comentario=''):
    hito = (
        Hito.objects.select_for_update(of=('self',))
        .select_related('proyecto')
        .get(pk=hito.pk)
    )
    if hito.proyecto.estado != Proyecto.Estado.EN_CURSO:
        raise EntregaNoPermitida("El proyecto ya está completado.")
    if hito.estado == Hito.Estado.ENTREGADO:
        raise EntregaNoPermitida("Este hito ya fue entregado y está pendiente de revisión.")
    if hito.estado == Hito.Estado.APROBADO:
        raise EntregaNoPermitida("Este hito ya fue aprobado.")

    ultima = hito.entregas.aggregate(m=Max('version'))['m'] or 0
    entrega = Entrega.objects.create(
        hito=hito,
        version=ultima + 1,
        archivo=archivo,
        comentario=comentario.strip(),
        subido_por=usuario,
    )
    hito.estado = Hito.Estado.ENTREGADO
    hito.save(update_fields=['estado', 'actualizado_en'])

    # El correo sale solo si la transacción se confirma y nunca rompe el flujo.
    transaction.on_commit(lambda: notificaciones.notificar_entrega(entrega.pk))
    return entrega


def verificar_cierre(proyecto):
    """Si todos los hitos están aprobados, completa el proyecto y emite la constancia (idempotente)."""
    hitos = proyecto.hitos.all()
    if not hitos.exists() or hitos.exclude(estado=Hito.Estado.APROBADO).exists():
        return None
    if proyecto.estado != Proyecto.Estado.COMPLETADO:
        proyecto.estado = Proyecto.Estado.COMPLETADO
        proyecto.save(update_fields=['estado', 'actualizado_en'])
        transaction.on_commit(lambda: notificaciones.notificar_proyecto_completado(proyecto.pk))
    constancia, _ = Constancia.objects.get_or_create(proyecto=proyecto)
    return constancia


@transaction.atomic
def registrar_revision(*, entrega, docente, observacion, calificacion, aprobada):
    hito = (
        Hito.objects.select_for_update(of=('self',))
        .select_related('proyecto')
        .get(pk=entrega.hito_id)
    )
    proyecto = hito.proyecto

    if proyecto.asesor_id != docente.pk:
        raise RevisionNoPermitida("No eres el asesor de este proyecto.")
    if proyecto.estado != Proyecto.Estado.EN_CURSO:
        raise RevisionNoPermitida("El proyecto ya está completado.")
    if hito.estado != Hito.Estado.ENTREGADO:
        raise RevisionNoPermitida("Este hito no está pendiente de revisión.")
    ultima = hito.entregas.order_by('-version').first()
    if ultima is None or ultima.pk != entrega.pk:
        raise RevisionNoPermitida("Existe una versión más reciente de esta entrega.")

    revision = Revision.objects.create(
        entrega=entrega,
        docente=docente,
        observacion=(observacion or '').strip(),
        calificacion=calificacion,
        aprobada=aprobada,
    )
    hito.estado = Hito.Estado.APROBADO if aprobada else Hito.Estado.OBSERVADO
    hito.save(update_fields=['estado', 'actualizado_en'])

    transaction.on_commit(lambda: notificaciones.notificar_revision(revision.pk))
    if aprobada:
        verificar_cierre(proyecto)
    return revision


# ── Repositorio público ─────────────────────────────────────
@transaction.atomic
def publicar_proyecto(*, proyecto, resumen):
    resumen = (resumen or '').strip()
    if proyecto.estado != Proyecto.Estado.COMPLETADO:
        raise PublicacionNoPermitida("Solo se pueden publicar proyectos completados.")
    if not resumen:
        raise PublicacionNoPermitida("El resumen público es obligatorio para publicar.")
    proyecto.resumen_publico = resumen
    if not proyecto.publicado or proyecto.fecha_publicacion is None:
        proyecto.fecha_publicacion = timezone.now()
    proyecto.publicado = True
    proyecto.save(update_fields=['resumen_publico', 'publicado', 'fecha_publicacion', 'actualizado_en'])
    return proyecto


@transaction.atomic
def despublicar_proyecto(*, proyecto):
    proyecto.publicado = False
    proyecto.save(update_fields=['publicado', 'actualizado_en'])
    return proyecto