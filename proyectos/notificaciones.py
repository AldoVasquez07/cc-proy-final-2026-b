"""Notificaciones por correo (Resend / Brevo vía HTTP) y recordatorios de hitos."""
import logging
from datetime import timedelta
from email.utils import parseaddr

import requests
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)

# Cron-job.org corta la petición a los 30 s: se procesa por lotes y el resto sale en la siguiente corrida.
LOTE_MAXIMO_ALERTAS = 25

RESEND_URL = 'https://api.resend.com/emails'
BREVO_URL = 'https://api.brevo.com/v3/smtp/email'


def _url(nombre_url, *args):
    return settings.SITE_URL.rstrip('/') + reverse(nombre_url, args=args)


def enviar_correo(destino, asunto, html):
    """Envía un correo por la API del proveedor. Nunca lanza excepciones. Devuelve True/False."""
    destinatarios = [destino] if isinstance(destino, str) else list(destino or [])
    destinatarios = [d for d in destinatarios if d]
    if not destinatarios:
        logger.warning("Correo '%s' sin destinatario: no se envía.", asunto)
        return False

    proveedor = (settings.EMAIL_PROVIDER or 'resend').lower()
    api_key = settings.BREVO_API_KEY if proveedor == 'brevo' else settings.RESEND_API_KEY
    if not api_key:
        logger.info("[correo sin API key] a=%s asunto=%s", destinatarios, asunto)
        return False

    try:
        if proveedor == 'brevo':
            nombre, email = parseaddr(settings.EMAIL_FROM)
            respuesta = requests.post(
                BREVO_URL,
                headers={'api-key': api_key, 'accept': 'application/json'},
                json={
                    'sender': {'name': nombre or 'TesisTrack', 'email': email},
                    'to': [{'email': d} for d in destinatarios],
                    'subject': asunto,
                    'htmlContent': html,
                },
                timeout=settings.EXTERNAL_API_TIMEOUT,
            )
        else:
            respuesta = requests.post(
                RESEND_URL,
                headers={'Authorization': f'Bearer {api_key}'},
                json={'from': settings.EMAIL_FROM, 'to': destinatarios, 'subject': asunto, 'html': html},
                timeout=settings.EXTERNAL_API_TIMEOUT,
            )
        if respuesta.status_code >= 400:
            logger.error("Error del proveedor de correo (%s): %s %s", proveedor, respuesta.status_code, respuesta.text[:300])
            return False
        return True
    except requests.RequestException:
        logger.exception("No se pudo contactar al proveedor de correo (%s).", proveedor)
        return False
    except Exception:
        logger.exception("Error inesperado al enviar correo.")
        return False


def _enviar_plantilla(destino, asunto, plantilla, contexto):
    html = render_to_string(plantilla, {**contexto, 'asunto': asunto, 'site_url': settings.SITE_URL})
    return enviar_correo(destino, asunto, html)


# ── Avisos disparados desde services (vía transaction.on_commit) ─────────
def notificar_entrega(entrega_id):
    from .models import Entrega
    entrega = Entrega.objects.select_related('hito__proyecto__asesor', 'hito__proyecto__estudiante').filter(pk=entrega_id).first()
    if entrega is None:
        return False
    proyecto = entrega.hito.proyecto
    return _enviar_plantilla(
        proyecto.asesor.email, f"Nueva entrega: {entrega.hito.titulo}", 'emails/nueva_entrega.html',
        {'entrega': entrega, 'hito': entrega.hito, 'proyecto': proyecto,
         'url': _url('proyectos:docente_proyecto_detail', proyecto.pk)},
    )


def notificar_revision(revision_id):
    from .models import Revision
    revision = Revision.objects.select_related(
        'entrega__hito__proyecto__estudiante', 'docente',
    ).filter(pk=revision_id).first()
    if revision is None:
        return False
    hito = revision.entrega.hito
    proyecto = hito.proyecto
    resultado = 'aprobado' if revision.aprobada else 'observado'
    return _enviar_plantilla(
        proyecto.estudiante.email, f"Tu hito «{hito.titulo}» fue {resultado}", 'emails/revision.html',
        {'revision': revision, 'hito': hito, 'proyecto': proyecto, 'resultado': resultado,
         'url': _url('proyectos:estudiante_proyecto_detail', proyecto.pk)},
    )


def notificar_proyecto_completado(proyecto_id):
    from .models import Proyecto
    proyecto = Proyecto.objects.select_related('estudiante', 'asesor').filter(pk=proyecto_id).first()
    if proyecto is None:
        return False
    return _enviar_plantilla(
        proyecto.estudiante.email, "¡Proyecto completado! Tu constancia está lista", 'emails/proyecto_completado.html',
        {'proyecto': proyecto, 'url': _url('proyectos:constancia', proyecto.pk)},
    )


# ── Recordatorios programados (Cron-job.org) ─────────────────────────────
def enviar_alertas_vencimiento():
    """Recuerda hitos PENDIENTE/OBSERVADO que vencen en ≤ 48 h (o ya vencidos) sin alerta previa."""
    from .models import Hito, Proyecto

    hoy = timezone.localdate()
    candidatos = (
        Hito.objects.filter(
            estado__in=(Hito.Estado.PENDIENTE, Hito.Estado.OBSERVADO),
            alerta_enviada=False,
            fecha_limite__lte=hoy + timedelta(days=2),
            proyecto__estado=Proyecto.Estado.EN_CURSO,
            proyecto__estudiante__is_active=True,
        ).select_related('proyecto__estudiante', 'proyecto__asesor').order_by('fecha_limite')[:LOTE_MAXIMO_ALERTAS]
    )
    enviados = fallidos = 0
    for hito in candidatos:
        # "Reclama" el hito de forma atómica para no duplicar envíos si el cron corre dos veces.
        if not Hito.objects.filter(pk=hito.pk, alerta_enviada=False).update(alerta_enviada=True):
            continue
        ok = _enviar_plantilla(
            hito.proyecto.estudiante.email, f"Recordatorio: «{hito.titulo}» vence pronto",
            'emails/recordatorio_hito.html',
            {'hito': hito, 'proyecto': hito.proyecto, 'vencido': hito.fecha_limite < hoy,
             'url': _url('proyectos:estudiante_proyecto_detail', hito.proyecto_id)},
        )
        if ok:
            enviados += 1
        else:
            Hito.objects.filter(pk=hito.pk).update(alerta_enviada=False)  # reintentar en la próxima corrida
            fallidos += 1
    return {'revisados': enviados + fallidos, 'enviados': enviados, 'fallidos': fallidos}