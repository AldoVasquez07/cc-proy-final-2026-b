from decimal import Decimal
from unittest import mock

import requests
from django.test import override_settings
from django.urls import reverse

from core.testing import TenantTestCase, crear_entrega, pdf
from proyectos import notificaciones
from proyectos.services import registrar_entrega, registrar_revision

POST = 'proyectos.notificaciones.requests.post'


def _ok():
    return mock.Mock(status_code=200, text='ok')


class EnviarCorreoTests(TenantTestCase):
    @override_settings(RESEND_API_KEY='re_test', EMAIL_PROVIDER='resend', EMAIL_FROM='TesisTrack <no-reply@x.com>')
    def test_resend_envia_payload_correcto(self):
        with mock.patch(POST, return_value=_ok()) as post:
            self.assertTrue(notificaciones.enviar_correo('a@b.com', 'Hola', '<p>x</p>'))
        args, kwargs = post.call_args
        self.assertEqual(args[0], notificaciones.RESEND_URL)
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer re_test')
        self.assertEqual(kwargs['json']['to'], ['a@b.com'])
        self.assertIn('timeout', kwargs)

    @override_settings(BREVO_API_KEY='br_test', EMAIL_PROVIDER='brevo', EMAIL_FROM='TesisTrack <no-reply@x.com>')
    def test_brevo_envia_payload_correcto(self):
        with mock.patch(POST, return_value=_ok()) as post:
            self.assertTrue(notificaciones.enviar_correo('a@b.com', 'Hola', '<p>x</p>'))
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs['headers']['api-key'], 'br_test')
        self.assertEqual(kwargs['json']['sender']['email'], 'no-reply@x.com')
        self.assertEqual(kwargs['json']['to'], [{'email': 'a@b.com'}])

    def test_sin_api_key_no_llama_a_la_red_ni_rompe(self):
        with mock.patch(POST) as post:
            self.assertFalse(notificaciones.enviar_correo('a@b.com', 'Hola', 'x'))
        post.assert_not_called()

    @override_settings(RESEND_API_KEY='re_test')
    def test_errores_de_red_y_http_no_lanzan_excepcion(self):
        with mock.patch(POST, side_effect=requests.Timeout):
            self.assertFalse(notificaciones.enviar_correo('a@b.com', 'Hola', 'x'))
        with mock.patch(POST, return_value=mock.Mock(status_code=500, text='boom')):
            self.assertFalse(notificaciones.enviar_correo('a@b.com', 'Hola', 'x'))

    @override_settings(RESEND_API_KEY='re_test')
    def test_sin_destinatario_no_envia(self):
        with mock.patch(POST) as post:
            self.assertFalse(notificaciones.enviar_correo('', 'Hola', 'x'))
        post.assert_not_called()


@override_settings(RESEND_API_KEY='re_test')
class DisparoDeCorreosTests(TenantTestCase):
    def test_entrega_avisa_al_asesor_solo_tras_commit(self):
        with mock.patch(POST, return_value=_ok()) as post:
            with self.captureOnCommitCallbacks(execute=True):
                registrar_entrega(hito=self.A.hito, usuario=self.A.est, archivo=pdf())
        self.assertEqual(post.call_count, 1)
        self.assertEqual(post.call_args.kwargs['json']['to'], [self.A.docente.email])

    def test_si_el_proveedor_falla_la_entrega_igual_se_registra(self):
        with mock.patch(POST, side_effect=requests.ConnectionError):
            with self.captureOnCommitCallbacks(execute=True):
                e = registrar_entrega(hito=self.A.hito, usuario=self.A.est, archivo=pdf())
        self.assertEqual(e.version, 1)

    def test_revision_avisa_al_estudiante_con_nota(self):
        e = crear_entrega(self.A.hito, self.A.est)
        with mock.patch(POST, return_value=_ok()) as post:
            with self.captureOnCommitCallbacks(execute=True):
                registrar_revision(entrega=e, docente=self.A.docente, observacion='Bien', calificacion=Decimal('18'), aprobada=True)
        envios = [c.kwargs['json'] for c in post.call_args_list]
        self.assertTrue(all(j['to'] == [self.A.est.email] for j in envios))
        self.assertEqual(len(envios), 2)  # revisión + proyecto completado
        revision = next(j for j in envios if 'aprobado' in j['subject'])
        self.assertIn('18', revision['html'])
        completado = next(j for j in envios if 'completado' in j['subject'].lower())
        self.assertIn(f'/constancias/proyecto/{self.A.proyecto.pk}/', completado['html'])


class RecuperacionPasswordTests(TenantTestCase):
    def test_flujo_de_recuperacion_envia_correo_y_no_revela_existencia(self):
        url = reverse('usuarios:password_reset')
        with mock.patch(POST, return_value=_ok()):
            r = self.client.post(url, {'email': 'noexiste@x.com'})
        self.assertRedirects(r, reverse('usuarios:password_reset_done'))
        with override_settings(RESEND_API_KEY='re_test', EMAIL_BACKEND='core.email_backend.ApiEmailBackend'):
            with mock.patch(POST, return_value=_ok()) as post:
                self.client.post(url, {'email': self.A.est.email})
        self.assertEqual(post.call_count, 1)
        self.assertIn('/password/restablecer/', post.call_args.kwargs['json']['html'])