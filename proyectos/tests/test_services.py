from decimal import Decimal
from unittest import mock

from core.testing import TenantTestCase, crear_entrega, pdf
from proyectos.models import Constancia, Hito, Proyecto
from proyectos.services import (
    EntregaNoPermitida, PublicacionNoPermitida, RevisionNoPermitida, despublicar_proyecto,
    publicar_proyecto, registrar_entrega, registrar_revision, verificar_cierre,
)


class EntregaServiceTests(TenantTestCase):
    def test_primera_entrega_v1_y_hito_entregado(self):
        e = registrar_entrega(hito=self.A.hito, usuario=self.A.est, archivo=pdf(), comentario=' hola ')
        self.A.hito.refresh_from_db()
        self.assertEqual(e.version, 1)
        self.assertEqual(e.comentario, 'hola')
        self.assertEqual(self.A.hito.estado, Hito.Estado.ENTREGADO)

    def test_versionado_tras_observacion(self):
        e1 = registrar_entrega(hito=self.A.hito, usuario=self.A.est, archivo=pdf())
        registrar_revision(entrega=e1, docente=self.A.docente, observacion='Corrige', calificacion=None, aprobada=False)
        e2 = registrar_entrega(hito=self.A.hito, usuario=self.A.est, archivo=pdf())
        self.assertEqual(e2.version, 2)

    def test_no_permite_entregar_si_ya_entregado_o_aprobado_o_completado(self):
        e = registrar_entrega(hito=self.A.hito, usuario=self.A.est, archivo=pdf())
        with self.assertRaises(EntregaNoPermitida):
            registrar_entrega(hito=self.A.hito, usuario=self.A.est, archivo=pdf())
        registrar_revision(entrega=e, docente=self.A.docente, observacion='', calificacion=Decimal('18'), aprobada=True)
        with self.assertRaises(EntregaNoPermitida):
            registrar_entrega(hito=self.A.hito, usuario=self.A.est, archivo=pdf())
        self.A.proyecto.refresh_from_db()
        self.assertEqual(self.A.proyecto.estado, Proyecto.Estado.COMPLETADO)


class RevisionServiceTests(TenantTestCase):
    def setUp(self):
        self.entrega = crear_entrega(self.A.hito, self.A.est)

    def test_observar_deja_hito_observado(self):
        r = registrar_revision(entrega=self.entrega, docente=self.A.docente, observacion=' Falta marco ', calificacion=None, aprobada=False)
        self.A.hito.refresh_from_db()
        self.assertEqual(self.A.hito.estado, Hito.Estado.OBSERVADO)
        self.assertFalse(r.aprobada)
        self.assertEqual(r.observacion, 'Falta marco')

    def test_aprobar_deja_hito_aprobado(self):
        registrar_revision(entrega=self.entrega, docente=self.A.docente, observacion='', calificacion=Decimal('17.5'), aprobada=True)
        self.A.hito.refresh_from_db()
        self.assertEqual(self.A.hito.estado, Hito.Estado.APROBADO)

    def test_solo_el_asesor_puede_revisar(self):
        with self.assertRaises(RevisionNoPermitida):
            registrar_revision(entrega=self.entrega, docente=self.B.docente, observacion='x', calificacion=None, aprobada=False)

    def test_no_revisa_hito_que_no_esta_entregado(self):
        registrar_revision(entrega=self.entrega, docente=self.A.docente, observacion='x', calificacion=None, aprobada=False)
        with self.assertRaises(RevisionNoPermitida):
            registrar_revision(entrega=self.entrega, docente=self.A.docente, observacion='x', calificacion=None, aprobada=False)

    def test_no_revisa_version_antigua(self):
        registrar_revision(entrega=self.entrega, docente=self.A.docente, observacion='x', calificacion=None, aprobada=False)
        e2 = registrar_entrega(hito=self.A.hito, usuario=self.A.est, archivo=pdf())
        with self.assertRaises(RevisionNoPermitida):
            registrar_revision(entrega=self.entrega, docente=self.A.docente, observacion='x', calificacion=None, aprobada=False)
        registrar_revision(entrega=e2, docente=self.A.docente, observacion='x', calificacion=None, aprobada=False)


class CierreYConstanciaTests(TenantTestCase):
    def test_cierre_requiere_todos_los_hitos_aprobados(self):
        h2 = Hito.objects.create(proyecto=self.A.proyecto, titulo='H2', fecha_limite=self.A.hito.fecha_limite, orden=2)
        e = crear_entrega(self.A.hito, self.A.est)
        registrar_revision(entrega=e, docente=self.A.docente, observacion='', calificacion=Decimal('15'), aprobada=True)
        self.A.proyecto.refresh_from_db()
        self.assertEqual(self.A.proyecto.estado, Proyecto.Estado.EN_CURSO)
        self.assertFalse(Constancia.objects.filter(proyecto=self.A.proyecto).exists())
        e2 = crear_entrega(h2, self.A.est)
        registrar_revision(entrega=e2, docente=self.A.docente, observacion='', calificacion=Decimal('16'), aprobada=True)
        self.A.proyecto.refresh_from_db()
        self.assertEqual(self.A.proyecto.estado, Proyecto.Estado.COMPLETADO)
        self.assertTrue(Constancia.objects.filter(proyecto=self.A.proyecto).exists())

    def test_emision_de_constancia_es_idempotente(self):
        self.A.hito.estado = Hito.Estado.APROBADO
        self.A.hito.save()
        c1 = verificar_cierre(self.A.proyecto)
        c2 = verificar_cierre(self.A.proyecto)
        self.assertEqual(c1.pk, c2.pk)
        self.assertEqual(Constancia.objects.filter(proyecto=self.A.proyecto).count(), 1)

    def test_proyecto_sin_hitos_no_se_completa(self):
        self.A.hito.delete()
        self.assertIsNone(verificar_cierre(self.A.proyecto))

    def test_correo_de_completado_se_envia_una_sola_vez(self):
        self.A.hito.estado = Hito.Estado.APROBADO
        self.A.hito.save()
        with mock.patch('proyectos.notificaciones.notificar_proyecto_completado') as aviso:
            with self.captureOnCommitCallbacks(execute=True):
                verificar_cierre(self.A.proyecto)
                verificar_cierre(self.A.proyecto)
        self.assertEqual(aviso.call_count, 1)


class PublicacionServiceTests(TenantTestCase):
    def _completar(self):
        self.A.hito.estado = Hito.Estado.APROBADO
        self.A.hito.save()
        verificar_cierre(self.A.proyecto)
        self.A.proyecto.refresh_from_db()

    def test_no_publica_proyecto_en_curso(self):
        with self.assertRaises(PublicacionNoPermitida):
            publicar_proyecto(proyecto=self.A.proyecto, resumen='Un resumen suficientemente largo para publicar.')

    def test_publica_y_despublica(self):
        self._completar()
        publicar_proyecto(proyecto=self.A.proyecto, resumen='  Un resumen suficientemente largo para publicar.  ')
        self.A.proyecto.refresh_from_db()
        self.assertTrue(self.A.proyecto.publicado)
        self.assertIsNotNone(self.A.proyecto.fecha_publicacion)
        self.assertTrue(self.A.proyecto.resumen_publico.startswith('Un resumen'))
        despublicar_proyecto(proyecto=self.A.proyecto)
        self.A.proyecto.refresh_from_db()
        self.assertFalse(self.A.proyecto.publicado)

    def test_exige_resumen(self):
        self._completar()
        with self.assertRaises(PublicacionNoPermitida):
            publicar_proyecto(proyecto=self.A.proyecto, resumen='   ')