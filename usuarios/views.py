from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import FormView, TemplateView
from django_otp import login as otp_login
from django_otp.plugins.otp_totp.models import TOTPDevice

from .forms import OTPForm, RegistroInstitucionForm
from .utils import clave_base32, qr_base64, redirigir_2fa


def _siguiente_seguro(request, default='usuarios:home'):
    destino = request.GET.get('next') or request.POST.get('next')
    if destino and url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
        return destino
    return reverse(default)


class RegistroInstitucionView(FormView):
    template_name = 'usuarios/registro.html'
    form_class = RegistroInstitucionForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('usuarios:home')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        usuario = form.save()
        login(self.request, usuario, backend='usuarios.backends.PerfilModelBackend')
        messages.success(self.request, "Institución registrada. Configura tu verificación en dos pasos.")
        return redirect('usuarios:2fa_configurar')


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'usuarios/home.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_superuser:
                return redirect('admin:index')
            if not request.user.is_verified():
                return redirigir_2fa(request)
        return super().dispatch(request, *args, **kwargs)


class Configurar2FAView(LoginRequiredMixin, FormView):
    template_name = 'usuarios/2fa_configurar.html'
    form_class = OTPForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if TOTPDevice.objects.filter(user=request.user, confirmed=True).exists():
                return redirect('usuarios:2fa_verificar')
            self.device = (
                TOTPDevice.objects.filter(user=request.user, confirmed=False).first()
                or TOTPDevice.objects.create(user=request.user, name='default', confirmed=False)
            )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['qr'] = qr_base64(self.device.config_url)
        ctx['clave'] = clave_base32(self.device)
        ctx['next'] = self.request.GET.get('next', '')
        return ctx

    def form_valid(self, form):
        if self.device.verify_token(form.cleaned_data['token']):
            self.device.confirmed = True
            self.device.save()
            otp_login(self.request, self.device)
            messages.success(self.request, "Verificación en dos pasos activada.")
            return redirect(_siguiente_seguro(self.request))
        form.add_error('token', "Código incorrecto. Inténtalo de nuevo.")
        return self.form_invalid(form)


class Verificar2FAView(LoginRequiredMixin, FormView):
    template_name = 'usuarios/2fa_verificar.html'
    form_class = OTPForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_verified():
                return redirect('usuarios:home')
            self.device = TOTPDevice.objects.filter(user=request.user, confirmed=True).first()
            if self.device is None:
                return redirect('usuarios:2fa_configurar')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['next'] = self.request.GET.get('next', '')
        return ctx

    def form_valid(self, form):
        if self.device.verify_token(form.cleaned_data['token']):
            otp_login(self.request, self.device)
            return redirect(_siguiente_seguro(self.request))
        form.add_error('token', "Código incorrecto o expirado.")
        return self.form_invalid(form)