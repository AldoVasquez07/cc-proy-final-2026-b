from django.conf import settings
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

from .forms import BootstrapPasswordChangeForm, BootstrapPasswordResetForm, BootstrapSetPasswordForm
from .utils import redirigir_2fa


class RecuperarPasswordView(auth_views.PasswordResetView):
    template_name = 'usuarios/password_reset_form.html'
    email_template_name = 'usuarios/emails/password_reset_email.txt'
    html_email_template_name = 'usuarios/emails/password_reset_email.html'
    subject_template_name = 'usuarios/emails/password_reset_subject.txt'
    form_class = BootstrapPasswordResetForm
    success_url = reverse_lazy('usuarios:password_reset_done')
    extra_email_context = {'site_url': settings.SITE_URL.rstrip('/')}


class RecuperarPasswordHechoView(auth_views.PasswordResetDoneView):
    template_name = 'usuarios/password_reset_done.html'


class RecuperarPasswordConfirmarView(auth_views.PasswordResetConfirmView):
    template_name = 'usuarios/password_reset_confirm.html'
    form_class = BootstrapSetPasswordForm
    success_url = reverse_lazy('usuarios:password_reset_complete')


class RecuperarPasswordCompletoView(auth_views.PasswordResetCompleteView):
    template_name = 'usuarios/password_reset_complete.html'


class CambiarPasswordView(auth_views.PasswordChangeView):
    """Requiere sesión (LoginRequired nativo) y 2FA verificado."""
    template_name = 'usuarios/password_change_form.html'
    form_class = BootstrapPasswordChangeForm
    success_url = reverse_lazy('usuarios:password_change_done')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_verified():
            return redirigir_2fa(request)
        return super().dispatch(request, *args, **kwargs)


class CambiarPasswordHechoView(auth_views.PasswordChangeDoneView):
    template_name = 'usuarios/password_change_done.html'