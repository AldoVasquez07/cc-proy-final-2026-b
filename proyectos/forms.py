from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from core.forms import BootstrapMixin
from core.models import Carrera, PeriodoAcademico
from usuarios import roles

from .models import Proyecto

Usuario = get_user_model()


class UsuarioChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        codigo = f" · {obj.codigo}" if obj.codigo else ""
        return f"{obj.nombre_completo}{codigo}"


class ProyectoForm(BootstrapMixin, forms.ModelForm):
    estudiante = UsuarioChoiceField(queryset=Usuario.objects.none(), label="Estudiante")
    asesor = UsuarioChoiceField(queryset=Usuario.objects.none(), label="Docente asesor")

    class Meta:
        model = Proyecto
        fields = ('periodo', 'carrera', 'estudiante', 'asesor', 'titulo', 'descripcion')
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 4})}

    def __init__(self, *args, institucion=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.institucion = institucion
        self.instance.institucion = institucion

        estudiante_actual = self.instance.estudiante_id if self.instance.pk else None
        asesor_actual = self.instance.asesor_id if self.instance.pk else None

        self.fields['periodo'].queryset = PeriodoAcademico.objects.filter(institucion=institucion)
        self.fields['carrera'].queryset = Carrera.objects.filter(institucion=institucion, activa=True)
        self.fields['carrera'].required = False
        self.fields['estudiante'].queryset = Usuario.objects.filter(
            Q(is_active=True) | Q(pk=estudiante_actual),
            institucion=institucion, rol=roles.ESTUDIANTE,
        ).order_by('last_name', 'first_name')
        self.fields['asesor'].queryset = Usuario.objects.filter(
            Q(is_active=True) | Q(pk=asesor_actual),
            institucion=institucion, rol=roles.DOCENTE,
        ).order_by('last_name', 'first_name')

        periodo_vigente = PeriodoAcademico.objects.filter(institucion=institucion, activo=True).first()
        if periodo_vigente and not self.instance.pk:
            self.fields['periodo'].initial = periodo_vigente

    def clean_titulo(self):
        return self.cleaned_data['titulo'].strip()

    def save(self, commit=True):
        proyecto = super().save(commit=False)
        if not proyecto.carrera_id and proyecto.estudiante_id and proyecto.estudiante.carrera_id:
            proyecto.carrera = proyecto.estudiante.carrera
        if commit:
            proyecto.save()
        return proyecto