from django.contrib import admin

from .models import Carrera, Institucion, PeriodoAcademico


@admin.register(Institucion)
class InstitucionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'dominio', 'plan', 'activa', 'creado_en')
    list_filter = ('plan', 'activa')
    search_fields = ('nombre', 'dominio')
    prepopulated_fields = {'slug': ('nombre',)}


@admin.register(Carrera)
class CarreraAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'institucion', 'activa')
    list_filter = ('institucion', 'activa')
    search_fields = ('codigo', 'nombre')


@admin.register(PeriodoAcademico)
class PeriodoAcademicoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'institucion', 'fecha_inicio', 'fecha_fin', 'activo')
    list_filter = ('institucion', 'activo')