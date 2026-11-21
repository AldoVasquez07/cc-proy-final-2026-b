from django.urls import reverse

from core.testing import TenantTestCase, login_2fa
from usuarios.models import Usuario


class PermisosYDosFactoresTests(TenantTestCase):
    def test_anonimo_redirige_al_login(self):
        r = self.client.get(reverse('proyectos:proyecto_list'))
        self.assertRedirects(r, f"{reverse('usuarios:login')}?next={reverse('proyectos:proyecto_list')}")

    def test_sin_2fa_redirige_a_configurar(self):
        self.client.force_login(self.A.coord)
        r = self.client.get(reverse('proyectos:proyecto_list'))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse('usuarios:2fa_configurar'), r['Location'])

    def test_vistas_privadas_exigen_2fa(self):
        self.client.force_login(self.A.docente)
        for nombre in ('proyectos:docente_proyecto_list', 'analitica:dashboard', 'usuarios:password_change'):
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 302, nombre)

    def test_docente_no_entra_a_vistas_de_coordinador(self):
        login_2fa(self.client, self.A.docente)
        for nombre in ('proyectos:proyecto_list', 'usuarios:docente_list', 'core:carrera_list'):
            self.assertRedirects(self.client.get(reverse(nombre)), reverse('usuarios:home'), fetch_redirect_response=False)

    def test_estudiante_no_entra_a_docente_ni_coordinador_ni_panel(self):
        login_2fa(self.client, self.A.est)
        for nombre in ('proyectos:docente_proyecto_list', 'proyectos:proyecto_list', 'analitica:dashboard'):
            self.assertRedirects(self.client.get(reverse(nombre)), reverse('usuarios:home'), fetch_redirect_response=False)

    def test_coordinador_no_entra_a_vistas_de_estudiante(self):
        login_2fa(self.client, self.A.coord)
        r = self.client.get(reverse('proyectos:estudiante_proyecto_list'))
        self.assertRedirects(r, reverse('usuarios:home'), fetch_redirect_response=False)

    def test_login_por_correo_y_rechazo_de_clave_incorrecta(self):
        ok = self.client.post(reverse('usuarios:login'), {'username': self.A.est.email, 'password': 'ClaveSegura#2026'})
        self.assertEqual(ok.status_code, 302)
        self.client.logout()
        mal = self.client.post(reverse('usuarios:login'), {'username': self.A.est.email, 'password': 'otra'})
        self.assertEqual(mal.status_code, 200)

    def test_institucion_inactiva_no_puede_ingresar(self):
        self.A.inst.activa = False
        self.A.inst.save()
        r = self.client.post(reverse('usuarios:login'), {'username': self.A.coord.email, 'password': 'ClaveSegura#2026'})
        self.assertEqual(r.status_code, 200)
        self.A.inst.activa = True
        self.A.inst.save()

    def test_contrasenas_se_guardan_con_hash_no_en_claro(self):
        u = Usuario.objects.get(pk=self.A.est.pk)
        self.assertNotIn('ClaveSegura', u.password)
        self.assertTrue(u.check_password('ClaveSegura#2026'))


class AislamientoUsuariosTests(TenantTestCase):
    def setUp(self):
        login_2fa(self.client, self.A.coord)

    def test_listados_no_muestran_usuarios_de_otra_institucion(self):
        docentes = self.client.get(reverse('usuarios:docente_list'))
        self.assertContains(docentes, self.A.docente.email)
        self.assertNotContains(docentes, self.B.docente.email)
        estudiantes = self.client.get(reverse('usuarios:estudiante_list'))
        self.assertContains(estudiantes, self.A.est.email)
        self.assertNotContains(estudiantes, self.B.est.email)

    def test_editar_o_desactivar_usuario_ajeno_da_404(self):
        self.assertEqual(self.client.get(reverse('usuarios:docente_update', args=[self.B.docente.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('usuarios:estudiante_update', args=[self.B.est.pk])).status_code, 404)
        r = self.client.post(reverse('usuarios:docente_toggle', args=[self.B.docente.pk]))
        self.assertEqual(r.status_code, 404)
        self.assertTrue(Usuario.objects.get(pk=self.B.docente.pk).is_active)