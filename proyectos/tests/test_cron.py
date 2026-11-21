from datetime import timedelta
from unittest import mock

from django.test import override_settings
from django.utils import timezone

from core.testing import TenantTestCase
from proyectos.forms import HitoForm
from proyectos.models import Hito

POST = 'proyectos.notificaciones.requests.post'
URL = '/cron/alertas/'


def _ok():
    return mock.Mock(status_code=200, text='ok')


@override_settings(RESEND_API_KEY='re_test')
class CronAlertasTests(TenantTestCase):
    def _hito(self, dias, estado=Hito.Estado.PENDIENTE):
        self.A.hito.fecha_limite = timezone.localdate() + timedelta(days=dias)
        self.A.hito.estado = estado
        self.A.hito.alerta_enviada = False
        self.A.hito.save()
        return self.A.hito

    def test_sin_token_o_token_invalido_da_403(self):
        self.assertEqual(self.client.get(URL).status_code, 403)
        self.assertEqual(self.client.get(URL, HTTP_X_CRON_TOKEN='incorrecto').status_code, 403)

    @override_settings(CRON_TOKEN='')
    def test_token_vacio_nunca_autoriza(self):
        self.assertEqual(self.client.get(URL, HTTP_X_CRON_TOKEN='').status_code, 403)

    def test_metodos_permitidos_solo_get_y_post(self):
        self.assertEqual(self.client.put(URL, HTTP_X_CRON_TOKEN='token-de-prueba').status_code, 405)
        self.assertEqual(self.client.delete(URL, HTTP_X_CRON_TOKEN='token-de-prueba').status_code, 405)

    def test_envia_recordatorio_y_no_repite(self):
        h = self._hito(1)
        with mock.patch(POST, return_value=_ok()) as post:
            r1 = self.client.post(URL, HTTP_X_CRON_TOKEN='token-de-prueba')
            r2 = self.client.get(URL, HTTP_X_CRON_TOKEN='token-de-prueba')
        self.assertEqual(r1.json()['enviados'], 1)
        self.assertEqual(r2.json()['enviados'], 0)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(post.call_args.kwargs['json']['to'], [self.A.est.email])
        h.refresh_from_db()
        self.assertTrue(h.alerta_enviada)

    def test_no_envia_si_vence_en_mas_de_48h_o_esta_entregado_o_aprobado(self):
        with mock.patch(POST, return_value=_ok()) as post:
            self._hito(5)
            self.client.get(URL, HTTP_X_CRON_TOKEN='token-de-prueba')
            self._hito(1, Hito.Estado.ENTREGADO)
            self.client.get(URL, HTTP_X_CRON_TOKEN='token-de-prueba')
            self._hito(1, Hito.Estado.APROBADO)
            self.client.get(URL, HTTP_X_CRON_TOKEN='token-de-prueba')
        post.assert_not_called()

    def test_observado_tambien_recibe_recordatorio(self):
        self._hito(2, Hito.Estado.OBSERVADO)
        with mock.patch(POST, return_value=_ok()):
            self.assertEqual(self.client.get(URL, HTTP_X_CRON_TOKEN='token-de-prueba').json()['enviados'], 1)

    def test_si_falla_el_envio_se_reintenta_en_la_proxima_corrida(self):
        h = self._hito(1)
        with mock.patch(POST, return_value=mock.Mock(status_code=500, text='x')):
            r = self.client.get(URL, HTTP_X_CRON_TOKEN='token-de-prueba').json()
        self.assertEqual((r['enviados'], r['fallidos']), (0, 1))
        h.refresh_from_db()
        self.assertFalse(h.alerta_enviada)

    def test_cambiar_fecha_limite_reinicia_la_alerta(self):
        h = self._hito(1)
        Hito.objects.filter(pk=h.pk).update(alerta_enviada=True)
        h.refresh_from_db()
        nueva = timezone.localdate() + timedelta(days=9)
        form = HitoForm(
            data={'titulo': h.titulo, 'descripcion': '', 'fecha_limite': nueva.isoformat(), 'orden': h.orden},
            instance=h, proyecto=h.proyecto,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        h.refresh_from_db()
        self.assertFalse(h.alerta_enviada)
        self.assertEqual(h.fecha_limite, nueva)