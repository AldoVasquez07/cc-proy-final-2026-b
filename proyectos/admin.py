from django.contrib import admin

from .models import Constancia, Entrega, Hito, Proyecto, Revision


class HitoInline(admin.TabularInline):
    model = Hito
    extra = 0
    fields = ('orden', 'titulo', 'fecha_limite', 'estado', 'alerta_enviada')


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'institucion', 'estudiante', 'asesor', 'periodo', 'estado', 'publicado')
    list_filter = ('institucion', 'estado', 'publicado', 'periodo')
    search_fields = ('titulo', 'estudiante__email', 'asesor__email')
    list_select_related = ('institucion', 'estudiante', 'asesor', 'periodo')
    readonly_fields = ('creado_en', 'actualizado_en')
    inlines = [HitoInline]


@admin.register(Hito)
class HitoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'proyecto', 'fecha_limite', 'estado', 'alerta_enviada')
    list_filter = ('estado', 'alerta_enviada')
    search_fields = ('titulo', 'proyecto__titulo')
    list_select_related = ('proyecto',)


@admin.register(Entrega)
class EntregaAdmin(admin.ModelAdmin):
    list_display = ('hito', 'version', 'subido_por', 'subido_en')
    list_select_related = ('hito', 'subido_por')
    readonly_fields = ('subido_en',)


@admin.register(Revision)
class RevisionAdmin(admin.ModelAdmin):
    list_display = ('entrega', 'docente', 'calificacion', 'aprobada', 'creado_en')
    list_filter = ('aprobada',)
    list_select_related = ('entrega', 'docente')


@admin.register(Constancia)
class ConstanciaAdmin(admin.ModelAdmin):
    list_display = ('proyecto', 'codigo', 'emitida_en')
    readonly_fields = ('codigo', 'emitida_en')
    search_fields = ('codigo', 'proyecto__titulo')