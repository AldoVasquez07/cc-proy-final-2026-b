from django import forms
from django.core.exceptions import ValidationError

from .models import Carrera, PeriodoAcademico


class BootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                css = 'form-check-input'
            elif isinstance(field.widget, forms.Select):
                css = 'form-select'
            else:
                css = 'form-control'
            field.widget.attrs.setdefault('class', css)


class CarreraForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Carrera
        fields = ('codigo', 'nombre', 'activa')

    def __init__(self, *args, institucion=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.institucion = institucion
        self.instance.institucion = institucion

    def clean_codigo(self):
        codigo = self.cleaned_data['codigo'].strip().upper()
        existe = Carrera.objects.filter(institucion=self.institucion, codigo=codigo).exclude(pk=self.instance.pk)
        if existe.exists():
            raise ValidationError("Ya existe una carrera con ese código en tu institución.")
        return codigo


class PeriodoForm(BootstrapMixin, forms.ModelForm):
    fecha_inicio = forms.DateField(label="Inicio", widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))
    fecha_fin = forms.DateField(label="Fin", widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))

    class Meta:
        model = PeriodoAcademico
        fields = ('nombre', 'fecha_inicio', 'fecha_fin', 'activo')

    def __init__(self, *args, institucion=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.institucion = institucion
        self.instance.institucion = institucion

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        existe = PeriodoAcademico.objects.filter(institucion=self.institucion, nombre=nombre).exclude(pk=self.instance.pk)
        if existe.exists():
            raise ValidationError("Ya existe un periodo con ese nombre en tu institución.")
        return nombre
    
    
