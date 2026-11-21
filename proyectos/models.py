import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models

from core.models import TimeStampedModel
from usuarios import roles


def validar_tamano_pdf(archivo):
    limite = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if archivo.size > limite:
        raise ValidationError(f"El archivo supera el límite de {settings.MAX_UPLOAD_SIZE_MB} MB.")


class Proyecto(TimeStampedModel):
    class Estado(models.TextChoices):
        EN_CURSO = 'EN_CURSO', 'En curso'
        COMPLETADO = 'COMPLETADO', 'Completado'

    institucion = models.ForeignKey('core.Institucion', on_delete=models.CASCADE, related_name='proyectos')
    periodo = models.ForeignKey('core.PeriodoAcademico', on_delete=models.PROTECT, related_name='proyectos')
    carrera = models.ForeignKey('core.Carrera', on_delete=models.SET_NULL, null=True, blank=True, related_name='proyectos')
    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='proyectos_como_estudiante',
    )
    asesor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='proyectos_como_asesor',
    )
    titulo = models.CharField("Título", max_length=250)
    descripcion = models.TextField("Descripción", blank=True)
    estado = models.CharField("Estado", max_length=12, choices=Estado.choices, default=Estado.EN_CURSO)

    # Repositorio público
    publicado = models.BooleanField("Publicado en repositorio", default=False)
    resumen_publico = models.TextField("Resumen público", blank=True)
    fecha_publicacion = models.DateTimeField("Fecha de publicación", null=True, blank=True)

    class Meta:
        verbose_name = "Proyecto"
        verbose_name_plural = "Proyectos"
        ordering = ['-creado_en']
        constraints = [
            models.UniqueConstraint(fields=['periodo', 'estudiante'], name='unico_proyecto_por_estudiante_y_periodo'),
        ]

    def clean(self):
        errores = {}
        if self.institucion_id:
            if self.estudiante_id and (
                self.estudiante.institucion_id != self.institucion_id or self.estudiante.rol != roles.ESTUDIANTE
            ):
                errores['estudiante'] = "El estudiante no pertenece a tu institución."
            if self.asesor_id and (
                self.asesor.institucion_id != self.institucion_id or self.asesor.rol != roles.DOCENTE
            ):
                errores['asesor'] = "El asesor no pertenece a tu institución."
            if self.periodo_id and self.periodo.institucion_id != self.institucion_id:
                errores['periodo'] = "El periodo no pertenece a tu institución."
        if errores:
            raise ValidationError(errores)

    @property
    def progreso(self):
        total = self.hitos.count()
        if not total:
            return 0
        aprobados = self.hitos.filter(estado=Hito.Estado.APROBADO).count()
        return round(aprobados * 100 / total)

    def __str__(self):
        return self.titulo


class Hito(TimeStampedModel):
    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        ENTREGADO = 'ENTREGADO', 'Entregado'
        OBSERVADO = 'OBSERVADO', 'Observado'
        APROBADO = 'APROBADO', 'Aprobado'

    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='hitos')
    titulo = models.CharField("Título", max_length=200)
    descripcion = models.TextField("Descripción", blank=True)
    fecha_limite = models.DateField("Fecha límite")
    orden = models.PositiveSmallIntegerField("Orden", default=1)
    estado = models.CharField("Estado", max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    alerta_enviada = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Hito"
        verbose_name_plural = "Hitos"
        ordering = ['orden', 'fecha_limite']

    def __str__(self):
        return f"{self.titulo} ({self.proyecto})"


class Entrega(models.Model):
    hito = models.ForeignKey(Hito, on_delete=models.CASCADE, related_name='entregas')
    version = models.PositiveIntegerField("Versión", default=1)
    archivo = models.FileField(
        "Archivo PDF", upload_to='entregas/%Y/%m/',
        validators=[FileExtensionValidator(['pdf']), validar_tamano_pdf],
    )
    comentario = models.TextField("Comentario del estudiante", blank=True)
    subido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='entregas')
    subido_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Entrega"
        verbose_name_plural = "Entregas"
        ordering = ['-version']
        unique_together = ('hito', 'version')

    def __str__(self):
        return f"{self.hito.titulo} v{self.version}"


class Revision(models.Model):
    entrega = models.ForeignKey(Entrega, on_delete=models.CASCADE, related_name='revisiones')
    docente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='revisiones')
    observacion = models.TextField("Observaciones", blank=True)
    calificacion = models.DecimalField(
        "Calificación", max_digits=4, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
    )
    aprobada = models.BooleanField("Aprobada", default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Revisión"
        verbose_name_plural = "Revisiones"
        ordering = ['-creado_en']

    def __str__(self):
        return f"Revisión de {self.entrega}"


class Constancia(models.Model):
    proyecto = models.OneToOneField(Proyecto, on_delete=models.CASCADE, related_name='constancia')
    codigo = models.UUIDField("Código de verificación", default=uuid.uuid4, unique=True, editable=False)
    emitida_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Constancia"
        verbose_name_plural = "Constancias"

    def __str__(self):
        return f"Constancia {self.codigo}"