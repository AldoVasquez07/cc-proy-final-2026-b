from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'nombre_completo', 'rol', 'institucion', 'is_active')
    list_filter = ('rol', 'institucion', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'codigo')
    fieldsets = UserAdmin.fieldsets + (
        ('TesisTrack', {'fields': ('institucion', 'rol', 'carrera', 'codigo')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('TesisTrack', {'fields': ('email', 'institucion', 'rol', 'carrera', 'codigo')}),
    )