from django.urls import reverse

from core.models import Carrera, PeriodoAcademico
from core.testing import TenantTestCase, login_2fa


class AislamientoCoreTests(TenantTestCase):
    def setUp(self):
        login_2fa(self.client, self.A.coord)

    def test_listado_carreras_solo_de_mi_institucion(self):
        r = self.client.get(reverse('core:carrera_list'))
        self.assertContains(r, self.A.carrera.nombre)
        self.assertNotContains(r, self.B.carrera.nombre)

    def test_listado_periodos_solo_de_mi_institucion(self):
        r = self.client.get(reverse('core:periodo_list'))
        self.assertContains(r, self.A.periodo.nombre)
        self.assertNotContains(r, self.B.periodo.nombre)

    def test_carrera_ajena_da_404(self):
        for nombre in ('carrera_update', 'carrera_delete'):
            self.assertEqual(self.client.get(reverse(f'core:{nombre}', args=[self.B.carrera.pk])).status_code, 404)

    def test_periodo_ajeno_da_404(self):
        for nombre in ('periodo_update', 'periodo_delete'):
            self.assertEqual(self.client.get(reverse(f'core:{nombre}', args=[self.B.periodo.pk])).status_code, 404)

    def test_no_se_puede_borrar_carrera_ajena_por_post(self):
        r = self.client.post(reverse('core:carrera_delete', args=[self.B.carrera.pk]))
        self.assertEqual(r.status_code, 404)
        self.assertTrue(Carrera.objects.filter(pk=self.B.carrera.pk).exists())

    def test_crear_carrera_se_asigna_a_mi_institucion(self):
        self.client.post(reverse('core:carrera_create'), {'codigo': 'zz1', 'nombre': 'Nueva', 'activa': 'on'})
        c = Carrera.objects.get(codigo='ZZ1')
        self.assertEqual(c.institucion, self.A.inst)

    def test_solo_un_periodo_activo_por_institucion(self):
        from datetime import date
        PeriodoAcademico.objects.create(
            institucion=self.A.inst, nombre='2027-I', fecha_inicio=date(2027, 1, 1),
            fecha_fin=date(2027, 6, 1), activo=True,
        )
        self.assertEqual(PeriodoAcademico.objects.filter(institucion=self.A.inst, activo=True).count(), 1)
        self.assertTrue(PeriodoAcademico.objects.get(pk=self.B.periodo.pk).activo)  # B no se afecta