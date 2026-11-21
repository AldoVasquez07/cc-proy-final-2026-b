from django.urls import reverse

from analitica import services
from core.testing import TenantTestCase, crear_entrega, login_2fa


class PanelAnaliticoTests(TenantTestCase):
    def test_roles_con_acceso(self):
        for usuario, esperado in ((self.A.coord, 200), (self.A.docente, 200), (self.A.est, 302)):
            self.client.logout()
            login_2fa(self.client, usuario)
            self.assertEqual(self.client.get(reverse('analitica:dashboard')).status_code, esperado, usuario.rol)

    def test_metricas_basicas(self):
        crear_entrega(self.A.hito, self.A.est)
        panel = services.construir_panel(institucion=self.A.inst)
        self.assertEqual(panel['por_revisar'], 1)
        self.assertEqual(panel['total_hitos'], 1)
        self.assertEqual(panel['carga_asesores'][0]['por_revisar'], 1)

    def test_dashboard_incluye_datos_json_y_filtra_periodo(self):
        login_2fa(self.client, self.A.coord)
        r = self.client.get(reverse('analitica:dashboard'), {'periodo': self.A.periodo.pk})
        self.assertContains(r, 'id="datos-graficos"')
        r = self.client.get(reverse('analitica:dashboard'), {'periodo': self.B.periodo.pk})  # periodo ajeno → ignorado
        self.assertEqual(r.context['periodo_sel'], '')