import base64
from io import BytesIO
from urllib.parse import urlencode

import qrcode
from django.shortcuts import redirect
from django.urls import reverse
from django_otp.plugins.otp_totp.models import TOTPDevice


def redirigir_2fa(request):
    tiene_dispositivo = TOTPDevice.objects.filter(user=request.user, confirmed=True).exists()
    nombre = 'usuarios:2fa_verificar' if tiene_dispositivo else 'usuarios:2fa_configurar'
    return redirect(f"{reverse(nombre)}?{urlencode({'next': request.get_full_path()})}")


def qr_base64(data):
    img = qrcode.make(data)
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode()


def clave_base32(device):
    return base64.b32encode(bytes.fromhex(device.key)).decode()