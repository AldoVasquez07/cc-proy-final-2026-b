"""Backend de correo de Django que envía por la API HTTP (Resend/Brevo) en vez de SMTP."""
from django.core.mail.backends.base import BaseEmailBackend
from django.utils.html import linebreaks


class ApiEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        from proyectos.notificaciones import enviar_correo

        enviados = 0
        for mensaje in email_messages:
            html = next((c for c, tipo in getattr(mensaje, 'alternatives', []) if tipo == 'text/html'), None)
            if html is None:
                html = linebreaks(mensaje.body)
            if enviar_correo(list(mensaje.to), mensaje.subject, html):
                enviados += 1
        return enviados