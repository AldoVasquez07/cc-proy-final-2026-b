from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm, SetPasswordForm  # noqa: E402

from core.models import Institucion, dominio_validator, Carrera
from . import roles

Usuario = get_user_model()


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            field.widget.attrs.setdefault('class', css)


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    username = forms.CharField(label="Usuario o correo", widget=forms.TextInput(attrs={'autofocus': True}))
    password = forms.CharField(label="Contraseña", strip=False, widget=forms.PasswordInput)

    error_messages = {
        'invalid_login': "Credenciales incorrectas o institución inactiva.",
        'inactive': "Esta cuenta está inactiva.",
    }


class RegistroInstitucionForm(BootstrapFormMixin, forms.Form):
    nombre_institucion = forms.CharField(label="Nombre de la institución", max_length=200)
    dominio = forms.CharField(
        label="Dominio institucional (opcional)", max_length=100, required=False,
        validators=[dominio_validator], help_text="Ej: @instituto.edu.pe",
    )
    first_name = forms.CharField(label="Nombres", max_length=150)
    last_name = forms.CharField(label="Apellidos", max_length=150)
    email = forms.EmailField(label="Correo electrónico")
    username = forms.CharField(label="Usuario", max_length=150)
    password1 = forms.CharField(label="Contraseña", strip=False, widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmar contraseña", strip=False, widget=forms.PasswordInput)

    def clean_nombre_institucion(self):
        nombre = self.cleaned_data['nombre_institucion'].strip()
        if Institucion.objects.filter(nombre__iexact=nombre).exists():
            raise ValidationError("Ya existe una institución con ese nombre.")
        return nombre

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise ValidationError("Este correo ya está registrado.")
        return email

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if Usuario.objects.filter(username__iexact=username).exists():
            raise ValidationError("Este nombre de usuario ya existe.")
        return username

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 and p2:
            if p1 != p2:
                self.add_error('password2', "Las contraseñas no coinciden.")
            else:
                try:
                    validate_password(p1)
                except ValidationError as e:
                    self.add_error('password1', e)
        return cleaned

    @transaction.atomic
    def save(self):
        data = self.cleaned_data
        institucion = Institucion.objects.create(
            nombre=data['nombre_institucion'],
            dominio=data.get('dominio', ''),
        )
        return Usuario.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password1'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            institucion=institucion,
            rol=roles.COORDINADOR,
        )


class OTPForm(BootstrapFormMixin, forms.Form):
    token = forms.CharField(
        label="Código de 6 dígitos", min_length=6, max_length=6,
        widget=forms.TextInput(attrs={
            'autocomplete': 'one-time-code', 'inputmode': 'numeric',
            'autofocus': True, 'placeholder': '123456',
        }),
    )

    def clean_token(self):
        token = self.cleaned_data['token'].strip()
        if not token.isdigit():
            raise ValidationError("El código debe contener solo números.")
        return token


class UsuarioGestionForm(BootstrapFormMixin, forms.ModelForm):
    password = forms.CharField(
        label="Contraseña", strip=False, required=False,
        widget=forms.PasswordInput(render_value=False),
    )

    class Meta:
        model = Usuario
        fields = ('first_name', 'last_name', 'username', 'email', 'codigo', 'carrera')
        labels = {
            'first_name': 'Nombres',
            'last_name': 'Apellidos',
            'username': 'Usuario',
            'email': 'Correo electrónico',
            'codigo': 'Código / DNI',
            'carrera': 'Carrera',
        }

    def __init__(self, *args, institucion=None, rol=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.institucion = institucion
        self.rol = rol
        self.fields['carrera'].queryset = Carrera.objects.filter(institucion=institucion, activa=True)
        self.fields['carrera'].required = False
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        if self.instance.pk:
            self.fields['password'].help_text = "Déjala en blanco para no cambiarla."
        else:
            self.fields['password'].required = True

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            validate_password(password)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.institucion = self.institucion
        user.rol = self.rol
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user
    

# ── Recuperación y cambio de contraseña (con estilos Bootstrap) ──────────

class BootstrapPasswordResetForm(BootstrapFormMixin, PasswordResetForm):
    email = forms.EmailField(label="Correo electrónico", max_length=254)


class BootstrapSetPasswordForm(BootstrapFormMixin, SetPasswordForm):
    pass


class BootstrapPasswordChangeForm(BootstrapFormMixin, PasswordChangeForm):
    pass