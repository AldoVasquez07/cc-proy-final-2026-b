from django.urls import reverse

from core.testing import TenantTestCase, crear_entrega, crear_tenant, crear_usuario, login_2fa
from proyectos.models import Hito, Proyecto
from usuarios import roles


class AislamientoProyectosTests(TenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.entrega_b = crear_entrega(cls.B.hito, cls.B.est)
        from proyectos.services import verificar_cierre
        cls.B.hito.estado = Hito.Estado.APROBADO
        cls.B.hito.save()
        verificar_cierre(cls.B.proyecto)  # B: proyecto completado con constancia

    def test_coordinador_a_no_ve_proyectos_de_b(self):
        login_2fa(self.client, self.A.coord)
        lista = self.client.get(reverse('proyectos:proyecto_list'))
        self.assertContains(lista, self.A.proyecto.titulo)
        self.assertNotContains(lista, self.B.proyecto.titulo)
        for nombre in ('proyecto_detail', 'proyecto_update', 'proyecto_delete'):
            r = self.client.get(reverse(f'proyectos:{nombre}', args=[self.B.proyecto.pk]))
            self.assertEqual(r.status_code, 404, nombre)
        r = self.client.post(reverse('proyectos:proyecto_publicar', args=[self.B.proyecto.pk]), {'resumen_publico': 'x' * 40})
        self.assertEqual(r.status_code, 404)

    def test_coordinador_a_no_descarga_ni_ve_constancia_de_b(self):
        login_2fa(self.client, self.A.coord)
        self.assertEqual(self.client.get(reverse('proyectos:entrega_descargar', args=[self.entrega_b.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('proyectos:constancia', args=[self.B.proyecto.pk])).status_code, 404)

    def test_docente_a_no_accede_a_cartera_hitos_ni_revisiones_de_b(self):
        login_2fa(self.client, self.A.docente)
        self.assertEqual(self.client.get(reverse('proyectos:docente_proyecto_detail', args=[self.B.proyecto.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('proyectos:hito_create', args=[self.B.proyecto.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('proyectos:hito_update', args=[self.B.hito.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('proyectos:hito_delete', args=[self.B.hito.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('proyectos:revision_create', args=[self.entrega_b.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('proyectos:entrega_descargar', args=[self.entrega_b.pk])).status_code, 404)

    def test_estudiante_a_no_accede_a_datos_de_b(self):
        login_2fa(self.client, self.A.est)
        self.assertEqual(self.client.get(reverse('proyectos:estudiante_proyecto_detail', args=[self.B.proyecto.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('proyectos:entrega_create', args=[self.B.hito.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('proyectos:entrega_descargar', args=[self.entrega_b.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('proyectos:constancia', args=[self.B.proyecto.pk])).status_code, 404)

    def test_aislamiento_dentro_de_la_misma_institucion(self):
        """Un docente/estudiante de A no ve proyectos de otro docente/estudiante de A."""
        otro_est = crear_usuario(self.A.inst, roles.ESTUDIANTE, 'est2a')
        otro_doc = crear_usuario(self.A.inst, roles.DOCENTE, 'doc2a')
        p2 = Proyecto.objects.create(
            institucion=self.A.inst, periodo=self.A.periodo, estudiante=otro_est, asesor=otro_doc, titulo='Proyecto Ajeno',
        )
        login_2fa(self.client, self.A.docente)
        self.assertEqual(self.client.get(reverse('proyectos:docente_proyecto_detail', args=[p2.pk])).status_code, 404)
        self.client.logout()
        login_2fa(self.client, self.A.est)
        self.assertEqual(self.client.get(reverse('proyectos:estudiante_proyecto_detail', args=[p2.pk])).status_code, 404)

    def test_panel_analitico_solo_cuenta_datos_propios(self):
        from analitica import services
        panel = services.construir_panel(institucion=self.A.inst)
        self.assertEqual(panel['total_proyectos'], 1)
        panel_doc = services.construir_panel(institucion=self.A.inst, asesor=self.A.docente)
        self.assertEqual(panel_doc['total_proyectos'], 1)
        otro = crear_tenant('C')
        self.assertEqual(services.construir_panel(institucion=otro.inst, asesor=self.A.docente)['total_proyectos'], 0)


class DescargasPermitidasTests(TenantTestCase):
    def test_actores_legitimos_si_descargan(self):
        entrega = crear_entrega(self.A.hito, self.A.est)
        for usuario in (self.A.coord, self.A.docente, self.A.est):
            self.client.logout()
            login_2fa(self.client, usuario)
            r = self.client.get(reverse('proyectos:entrega_descargar', args=[entrega.pk]))
            self.assertEqual(r.status_code, 302, usuario.rol)