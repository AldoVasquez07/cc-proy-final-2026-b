from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Max, Q
from django.utils import timezone

from core.forms import BootstrapMixin
from core.models import Carrera, PeriodoAcademico
from usuarios import roles

from .models import Entrega, Hito, Proyecto, Revision

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


class HitoForm(BootstrapMixin, forms.ModelForm):
    fecha_limite = forms.DateField(
        label="Fecha límite",
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
    )
    orden = forms.IntegerField(
        label="Orden", min_value=1, required=False,
        help_text="Déjalo en blanco para ubicarlo al final.",
    )

    class Meta:
        model = Hito
        fields = ('titulo', 'descripcion', 'fecha_limite', 'orden')
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, proyecto=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.proyecto = proyecto
        self.instance.proyecto = proyecto

    def clean_titulo(self):
        return self.cleaned_data['titulo'].strip()

    def clean_fecha_limite(self):
        fecha = self.cleaned_data['fecha_limite']
        cambio = not self.instance.pk or 'fecha_limite' in self.changed_data
        if cambio and fecha < timezone.localdate():
            raise ValidationError("La fecha límite no puede estar en el pasado.")
        return fecha

    def clean_orden(self):
        orden = self.cleaned_data.get('orden')
        if orden:
            return orden
        if self.instance.pk:
            return self.instance.orden
        maximo = self.proyecto.hitos.aggregate(m=Max('orden'))['m'] or 0
        return maximo + 1

    def save(self, commit=True):
        hito = super().save(commit=False)
        # Si el docente cambia la fecha límite, el recordatorio puede volver a enviarse.
        if self.instance.pk and 'fecha_limite' in self.changed_data:
            hito.alerta_enviada = False
        if commit:
            hito.save()
        return hito


class EntregaForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Entrega
        fields = ('archivo', 'comentario')
        labels = {'archivo': 'Archivo PDF', 'comentario': 'Comentario para tu asesor (opcional)'}
        widgets = {
            'archivo': forms.FileInput(attrs={'accept': 'application/pdf'}),
            'comentario': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_archivo(self):
        archivo = self.cleaned_data['archivo']
        cabecera = archivo.read(5)
        archivo.seek(0)
        if not cabecera.startswith(b'%PDF'):
            raise ValidationError("El archivo no es un PDF válido.")
        return archivo


class RevisionForm(BootstrapMixin, forms.ModelForm):
    DECISIONES = (
        ('', '— Selecciona —'),
        ('APROBAR', 'Aprobar hito'),
        ('OBSERVAR', 'Devolver con observaciones'),
    )
    decision = forms.ChoiceField(label="Decisión", choices=DECISIONES)

    field_order = ['decision', 'calificacion', 'observacion']

    class Meta:
        model = Revision
        fields = ('calificacion', 'observacion')
        labels = {'calificacion': 'Calificación (0 - 20)', 'observacion': 'Observaciones'}
        widgets = {
            'calificacion': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '20'}),
            'observacion': forms.Textarea(attrs={'rows': 5}),
        }

    def clean(self):
        cleaned = super().clean()
        decision = cleaned.get('decision')
        if decision == 'APROBAR' and cleaned.get('calificacion') is None and 'calificacion' not in self.errors:
            self.add_error('calificacion', "Ingresa la calificación para aprobar el hito.")
        if decision == 'OBSERVAR' and not (cleaned.get('observacion') or '').strip():
            self.add_error('observacion', "Describe las observaciones para el estudiante.")
        return cleaned


class PublicacionForm(forms.Form):
    resumen_publico = forms.CharField(label="Resumen público", max_length=3000, strip=True)

    def clean_resumen_publico(self):
        resumen = self.cleaned_data['resumen_publico'].strip()
        if len(resumen) < 30:
            raise ValidationError("El resumen público debe tener al menos 30 caracteres.")
        return resumen