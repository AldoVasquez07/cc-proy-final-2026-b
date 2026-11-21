from django.urls import reverse

from core.testing import TenantTestCase, login_2fa
from proyectos.models import Hito, Proyecto
from proyectos.services import publicar_proyecto, verificar_cierre

RESUMEN = 'Resumen público suficientemente largo del proyecto de prueba.'


class RepositorioPublicoTests(TenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        for t in (cls.A, cls.B):
            t.hito.estado = Hito.Estado.APROBADO
            t.hito.save()
            verificar_cierre(t.proyecto)
            t.proyecto.refresh_from_db()
        publicar_proyecto(proyecto=cls.A.proyecto, resumen=RESUMEN)  # A publicado, B completado sin publicar

    def test_lista_anonima_muestra_solo_publicados(self):
        r = self.client.get(reverse('proyectos:repositorio_list'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.A.proyecto.titulo)
        self.assertNotContains(r, self.B.proyecto.titulo)

    def test_detalle_de_no_publicado_da_404(self):
        self.assertEqual(self.client.get(reverse('proyectos:repositorio_detail', args=[self.B.proyecto.pk])).status_code, 404)

    def test_proyecto_en_curso_marcado_publicado_no_aparece(self):
        p = Proyecto.objects.get(pk=self.B.proyecto.pk)
        Proyecto.objects.filter(pk=p.pk).update(estado=Proyecto.Estado.EN_CURSO, publicado=True)
        self.assertEqual(self.client.get(reverse('proyectos:repositorio_detail', args=[p.pk])).status_code, 404)

    def test_institucion_inactiva_oculta_sus_proyectos(self):
        self.A.inst.activa = False
        self.A.inst.save()
        self.assertNotContains(self.client.get(reverse('proyectos:repositorio_list')), self.A.proyecto.titulo)
        self.A.inst.activa = True
        self.A.inst.save()

    def test_detalle_no_expone_datos_privados(self):
        r = self.client.get(reverse('proyectos:repositorio_detail', args=[self.A.proyecto.pk]))
        self.assertContains(r, RESUMEN)
        self.assertContains(r, self.A.est.nombre_completo)
        self.assertContains(r, reverse('proyectos:constancia_verificar', args=[self.A.proyecto.constancia.codigo]))
        for privado in (self.A.est.email, self.A.docente.email, self.A.est.codigo, 'Descripción privada', '/entregas/', 'descargar'):
            self.assertNotContains(r, privado)

    def test_filtros_y_busqueda(self):
        url = reverse('proyectos:repositorio_list')
        self.assertContains(self.client.get(url, {'q': 'proyecto a'}), self.A.proyecto.titulo)
        self.assertNotContains(self.client.get(url, {'q': 'zzz-no-existe'}), self.A.proyecto.titulo)
        self.assertContains(self.client.get(url, {'institucion': self.A.inst.slug}), self.A.proyecto.titulo)
        self.assertNotContains(self.client.get(url, {'institucion': self.B.inst.slug}), self.A.proyecto.titulo)
        self.assertContains(self.client.get(url, {'carrera': self.A.carrera.nombre}), self.A.proyecto.titulo)
        self.assertContains(self.client.get(url, {'periodo': self.A.periodo.nombre}), self.A.proyecto.titulo)
        self.assertEqual(self.client.get(url, {'anio': 'abc'}).status_code, 200)
        self.assertNotContains(self.client.get(url, {'anio': '1999'}), self.A.proyecto.titulo)

    def test_sin_login_y_con_login_funciona(self):
        login_2fa(self.client, self.A.est)
        self.assertEqual(self.client.get(reverse('proyectos:repositorio_list')).status_code, 200)


class PublicarViewTests(TenantTestCase):
    def setUp(self):
        self.A.hito.estado = Hito.Estado.APROBADO
        self.A.hito.save()
        verificar_cierre(self.A.proyecto)

    def test_solo_coordinador_y_solo_post(self):
        url = reverse('proyectos:proyecto_publicar', args=[self.A.proyecto.pk])
        login_2fa(self.client, self.A.docente)
        self.client.post(url, {'resumen_publico': RESUMEN})
        self.A.proyecto.refresh_from_db()
        self.assertFalse(self.A.proyecto.publicado)
        self.client.logout()
        login_2fa(self.client, self.A.coord)
        self.assertEqual(self.client.get(url).status_code, 405)

    def test_coordinador_publica_y_despublica(self):
        login_2fa(self.client, self.A.coord)
        url = reverse('proyectos:proyecto_publicar', args=[self.A.proyecto.pk])
        self.client.post(url, {'accion': 'publicar', 'resumen_publico': RESUMEN})
        self.A.proyecto.refresh_from_db()
        self.assertTrue(self.A.proyecto.publicado)
        self.client.post(url, {'accion': 'despublicar'})
        self.A.proyecto.refresh_from_db()
        self.assertFalse(self.A.proyecto.publicado)

    def test_resumen_corto_se_rechaza(self):
        login_2fa(self.client, self.A.coord)
        self.client.post(reverse('proyectos:proyecto_publicar', args=[self.A.proyecto.pk]), {'accion': 'publicar', 'resumen_publico': 'corto'})
        self.A.proyecto.refresh_from_db()
        self.assertFalse(self.A.proyecto.publicado)