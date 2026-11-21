"""Utilidades compartidas por las pruebas (no son pruebas)."""
from datetime import timedelta
from types import SimpleNamespace

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_totp.models import TOTPDevice

from core.models import Carrera, Institucion, PeriodoAcademico
from proyectos.models import Entrega, Hito, Proyecto
from usuarios import roles
from usuarios.models import Usuario

PDF_VALIDO = b'%PDF-1.4\n%prueba\n'

AJUSTES_TEST = dict(
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
    SECURE_SSL_REDIRECT=False,
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    RESEND_API_KEY='', BREVO_API_KEY='', EMAIL_PROVIDER='resend',
    CRON_TOKEN='token-de-prueba', SITE_URL='http://testserver',
    ALLOWED_HOSTS=['testserver'],
)


def pdf(nombre='avance.pdf', contenido=PDF_VALIDO):
    return SimpleUploadedFile(nombre, contenido, content_type='application/pdf')


def login_2fa(client, usuario):
    """Inicia sesión y marca la sesión como verificada con 2FA (TOTP)."""
    dispositivo = TOTPDevice.objects.create(user=usuario, name='default', confirmed=True)
    client.force_login(usuario)
    sesion = client.session
    sesion[DEVICE_ID_SESSION_KEY] = dispositivo.persistent_id
    sesion.save()


def crear_usuario(institucion, rol, nombre, carrera=None):
    return Usuario.objects.create_user(
        username=nombre, email=f'{nombre}@ejemplo.edu.pe', password='ClaveSegura#2026',
        first_name=nombre.capitalize(), last_name='Prueba', institucion=institucion, rol=rol,
        carrera=carrera, codigo=f'COD-{nombre}',
    )


def crear_tenant(sufijo, dias_limite=10):
    """Institución completa: coordinador, docente, estudiante, periodo, carrera, proyecto e hito."""
    inst = Institucion.objects.create(nombre=f'Instituto {sufijo}')
    carrera = Carrera.objects.create(institucion=inst, codigo=f'C{sufijo}', nombre=f'Carrera {sufijo}')
    hoy = timezone.localdate()
    periodo = PeriodoAcademico.objects.create(
        institucion=inst, nombre=f'2026-{sufijo}', fecha_inicio=hoy - timedelta(days=30),
        fecha_fin=hoy + timedelta(days=120), activo=True,
    )
    coord = crear_usuario(inst, roles.COORDINADOR, f'coord{sufijo}')
    docente = crear_usuario(inst, roles.DOCENTE, f'doc{sufijo}')
    est = crear_usuario(inst, roles.ESTUDIANTE, f'est{sufijo}', carrera=carrera)
    proyecto = Proyecto.objects.create(
        institucion=inst, periodo=periodo, carrera=carrera, estudiante=est, asesor=docente,
        titulo=f'Proyecto {sufijo}', descripcion='Descripción privada',
    )
    hito = Hito.objects.create(proyecto=proyecto, titulo=f'Hito {sufijo}', fecha_limite=hoy + timedelta(days=dias_limite))
    return SimpleNamespace(
        inst=inst, carrera=carrera, periodo=periodo, coord=coord, docente=docente,
        est=est, proyecto=proyecto, hito=hito,
    )


def crear_entrega(hito, usuario, version=1):
    entrega = Entrega.objects.create(hito=hito, version=version, archivo=pdf(), subido_por=usuario)
    hito.estado = Hito.Estado.ENTREGADO
    hito.save()
    return entrega


@override_settings(**AJUSTES_TEST)
class TenantTestCase(TestCase):
    """Base: dos instituciones (A y B) aisladas, almacenamiento en memoria y hash rápido."""

    @classmethod
    def setUpTestData(cls):
        cls.A = crear_tenant('A')
        cls.B = crear_tenant('B')