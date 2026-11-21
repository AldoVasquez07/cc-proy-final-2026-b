import hmac
import logging

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .notificaciones import enviar_alertas_vencimiento

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def cron_alertas(request):
    """Endpoint para Cron-job.org. Header requerido: X-Cron-Token."""
    esperado = settings.CRON_TOKEN
    recibido = request.headers.get('X-Cron-Token', '')
    if not esperado or not hmac.compare_digest(recibido.encode(), esperado.encode()):
        logger.warning("Intento de acceso a /cron/alertas/ con token inválido.")
        return JsonResponse({'error': 'No autorizado.'}, status=403)
    return JsonResponse(enviar_alertas_vencimiento())