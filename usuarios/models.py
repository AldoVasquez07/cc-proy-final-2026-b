from django.contrib.auth.models import AbstractUser
from django.db import models

from . import roles


class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        COORDINADOR = roles.COORDINADOR, 'Coordinador Académico'
        DOCENTE = roles.DOCENTE, 'Docente Asesor'
        ESTUDIANTE = roles.ESTUDIANTE, 'Estudiante'

    email = models.EmailField("Correo electrónico", unique=True)
    institucion = models.ForeignKey(
        'core.Institucion', on_delete=models.PROTECT,
        related_name='usuarios', null=True, blank=True,
    )
    rol = models.CharField("Rol", max_length=12, choices=Rol.choices, blank=True)
    carrera = models.ForeignKey(
        'core.Carrera', on_delete=models.SET_NULL,
        related_name='usuarios', null=True, blank=True,
    )
    codigo = models.CharField("Código / DNI", max_length=20, blank=True)

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    @property
    def nombre_completo(self):
        return self.get_full_name() or self.username

    @property
    def es_coordinador(self):
        return self.rol == roles.COORDINADOR

    @property
    def es_docente(self):
        return self.rol == roles.DOCENTE

    @property
    def es_estudiante(self):
        return self.rol == roles.ESTUDIANTE

    def __str__(self):
        return f"{self.nombre_completo} ({self.get_rol_display() or 'Sin rol'})"