from django.contrib import admin

from .models import Constancia, Entrega, Hito, Proyecto, Revision


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'institucion', 'estudiante', 'asesor', 'periodo', 'estado', 'publicado')
    list_filter = ('institucion', 'estado', 'publicado')
    search_fields = ('titulo',)


@admin.register(Hito)
class HitoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'proyecto', 'fecha_limite', 'estado')
    list_filter = ('estado',)


@admin.register(Entrega)
class EntregaAdmin(admin.ModelAdmin):
    list_display = ('hito', 'version', 'subido_por', 'subido_en')


@admin.register(Revision)
class RevisionAdmin(admin.ModelAdmin):
    list_display = ('entrega', 'docente', 'calificacion', 'aprobada', 'creado_en')


@admin.register(Constancia)
class ConstanciaAdmin(admin.ModelAdmin):
    list_display = ('proyecto', 'codigo', 'emitida_en')