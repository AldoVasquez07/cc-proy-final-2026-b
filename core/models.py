from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils.text import slugify


def logo_storage():
    from django.conf import settings
    if getattr(settings, 'CLOUDINARY_CONFIGURADO', False):
        from cloudinary_storage.storage import MediaCloudinaryStorage
        return MediaCloudinaryStorage()
    from django.core.files.storage import FileSystemStorage
    return FileSystemStorage()


dominio_validator = RegexValidator(
    regex=r'^@[\w\-]+(\.[\w\-]+)+$',
    message="El dominio debe tener el formato '@instituto.edu.pe' (inicia con @ y contiene al menos un punto).",
)


class TimeStampedModel(models.Model):
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Institucion(TimeStampedModel):
    class Plan(models.TextChoices):
        GRATUITO = 'GRATUITO', 'Gratuito'
        BASICO = 'BASICO', 'Básico'
        PREMIUM = 'PREMIUM', 'Premium'

    nombre = models.CharField("Nombre", max_length=200, unique=True)
    slug = models.SlugField("Identificador", max_length=220, unique=True, blank=True)
    dominio = models.CharField(
        "Dominio institucional", max_length=100, blank=True,
        validators=[dominio_validator],
        help_text="Ej: @lasalle.edu.pe",
    )
    logo = models.ImageField("Logo", upload_to="instituciones/logos/", storage=logo_storage, blank=True, null=True)
    plan = models.CharField("Plan SaaS", max_length=10, choices=Plan.choices, default=Plan.GRATUITO)
    activa = models.BooleanField("Activa", default=True)

    class Meta:
        verbose_name = "Institución"
        verbose_name_plural = "Instituciones"
        ordering = ['nombre']

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.nombre)[:200]
            slug = base
            n = 2
            while Institucion.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class Carrera(TimeStampedModel):
    institucion = models.ForeignKey(Institucion, on_delete=models.CASCADE, related_name='carreras')
    codigo = models.CharField("Código", max_length=20)
    nombre = models.CharField("Nombre", max_length=200)
    activa = models.BooleanField("Activa", default=True)

    class Meta:
        verbose_name = "Carrera"
        verbose_name_plural = "Carreras"
        ordering = ['nombre']
        unique_together = ('institucion', 'codigo')

    def __str__(self):
        return f"{self.nombre} ({self.institucion.nombre})"


class PeriodoAcademico(TimeStampedModel):
    institucion = models.ForeignKey(Institucion, on_delete=models.CASCADE, related_name='periodos')
    nombre = models.CharField("Nombre", max_length=50, help_text="Ej: 2026-II")
    fecha_inicio = models.DateField("Inicio")
    fecha_fin = models.DateField("Fin")
    activo = models.BooleanField("Vigente", default=False)

    class Meta:
        verbose_name = "Periodo académico"
        verbose_name_plural = "Periodos académicos"
        ordering = ['-fecha_inicio']
        unique_together = ('institucion', 'nombre')

    def clean(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin <= self.fecha_inicio:
            raise ValidationError("La fecha de fin debe ser posterior a la de inicio.")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.activo:
            PeriodoAcademico.objects.filter(institucion=self.institucion).exclude(pk=self.pk).update(activo=False)

    def __str__(self):
        return f"{self.nombre} - {self.institucion.nombre}"