from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from core.testing import PDF_VALIDO, TenantTestCase, login_2fa, pdf
from proyectos.forms import EntregaForm
from proyectos.models import Entrega


class ValidacionPdfTests(TenantTestCase):
    def _form(self, archivo):
        return EntregaForm(data={'comentario': ''}, files={'archivo': archivo})

    def test_pdf_valido(self):
        self.assertTrue(self._form(pdf()).is_valid())

    def test_rechaza_extension_incorrecta(self):
        f = SimpleUploadedFile('avance.docx', PDF_VALIDO, content_type='application/pdf')
        self.assertFalse(self._form(f).is_valid())

    def test_rechaza_firma_falsa(self):
        f = SimpleUploadedFile('avance.pdf', b'MZ\x90\x00 no soy pdf', content_type='application/pdf')
        form = self._form(f)
        self.assertFalse(form.is_valid())
        self.assertIn('archivo', form.errors)

    @override_settings(MAX_UPLOAD_SIZE_MB=1)
    def test_rechaza_archivo_muy_grande(self):
        grande = SimpleUploadedFile('avance.pdf', PDF_VALIDO + b'0' * (1024 * 1024 + 10), content_type='application/pdf')
        self.assertFalse(self._form(grande).is_valid())

    def test_subida_por_vista_crea_entrega_y_muestra_limite(self):
        login_2fa(self.client, self.A.est)
        url = reverse('proyectos:entrega_create', args=[self.A.hito.pk])
        self.assertContains(self.client.get(url), 'máximo 10 MB')
        r = self.client.post(url, {'archivo': pdf(), 'comentario': 'ok'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Entrega.objects.filter(hito=self.A.hito).count(), 1)

    def test_vista_rechaza_falso_pdf(self):
        login_2fa(self.client, self.A.est)
        url = reverse('proyectos:entrega_create', args=[self.A.hito.pk])
        r = self.client.post(url, {'archivo': SimpleUploadedFile('x.pdf', b'basura'), 'comentario': ''})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Entrega.objects.count(), 0)