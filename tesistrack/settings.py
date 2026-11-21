"""
Configuración de TesisTrack (SaaS multi-tenant de seguimiento de proyectos integradores).

Stack: Django 5 en Vercel (Python Functions, WSGI) · Supabase (PostgreSQL) · Cloudinary (PDFs)
       Resend/Brevo (correos) · Cron-job.org (alertas) · QuickChart (QR)

Todos los secretos y valores por entorno se leen con python-decouple (.env / variables de entorno de Vercel).
Nunca escribir claves directamente en este archivo.
"""

from pathlib import Path

from decouple import Csv, config

# ══════════════════════════════════════════════════════════════
# 1. RUTAS BASE
# ══════════════════════════════════════════════════════════════
BASE_DIR = Path(__file__).resolve().parent.parent

# ══════════════════════════════════════════════════════════════
# 2. SEGURIDAD BÁSICA
# ══════════════════════════════════════════════════════════════
SECRET_KEY = config('SECRET_KEY')

# False por defecto: si se olvida la variable en producción, queda seguro.
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Vercel define VERCEL=1 y expone los hosts del despliegue (sin esquema) como variables de sistema.
ON_VERCEL = config('VERCEL', default=False, cast=bool)
_hosts_vercel = [
    h for h in (
        config('VERCEL_URL', default=''),
        config('VERCEL_BRANCH_URL', default=''),
        config('VERCEL_PROJECT_PRODUCTION_URL', default=''),
    ) if h
]
if ON_VERCEL:
    ALLOWED_HOSTS.append('.vercel.app')
ALLOWED_HOSTS.extend(h for h in _hosts_vercel if h not in ALLOWED_HOSTS)

# Django 4+ exige el esquema (https://) en los orígenes de confianza para CSRF.
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())
CSRF_TRUSTED_ORIGINS.extend(f'https://{h}' for h in _hosts_vercel)

# ══════════════════════════════════════════════════════════════
# 3. APLICACIONES
# ══════════════════════════════════════════════════════════════
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Va DESPUÉS de staticfiles: los estáticos los sirve Whitenoise y, si va antes, su comando
    # `collectstatic` (pensado para estáticos en Cloudinary) no copia los archivos y el build falla.
    'cloudinary_storage',

    # Terceros
    'cloudinary',
    'django_otp',                       # 2FA
    'django_otp.plugins.otp_totp',      # 2FA por app autenticadora (TOTP)
    'django_otp.plugins.otp_static',    # Códigos de respaldo

    # Apps propias (una por dominio, como en el proyecto de referencia)
    'core',         # Landing, instituciones (tenants), carreras, periodos
    'usuarios',     # Auth, roles (RBAC), 2FA
    'proyectos',    # Proyectos, hitos, entregas, revisiones, constancias
    'analitica',    # Dashboard y reportes
]

# ══════════════════════════════════════════════════════════════
# 4. MIDDLEWARE (el orden importa)
# ══════════════════════════════════════════════════════════════
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',      # Justo después de SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',             # Después de AuthenticationMiddleware
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'tesistrack.urls'

# ══════════════════════════════════════════════════════════════
# 5. PLANTILLAS
# ══════════════════════════════════════════════════════════════
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Inyecta nombre/logo de la institución del usuario en todas las plantillas
                'core.context_processors.institucion_actual',
            ],
        },
    },
]

WSGI_APPLICATION = 'tesistrack.wsgi.application'

# ══════════════════════════════════════════════════════════════
# 6. BASE DE DATOS (Supabase - PostgreSQL)
# ══════════════════════════════════════════════════════════════
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='postgres'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', default='5432'),
        # En serverless cada invocación abre/cierra su conexión (el pooler de Supabase las reutiliza).
        'CONN_MAX_AGE': config('DB_CONN_MAX_AGE', default=0 if ON_VERCEL else 60, cast=int),
        'OPTIONS': {
            'sslmode': config('DB_SSLMODE', default='require'),  # Supabase exige SSL
        },
        # Necesario con el pooler de Supabase en modo "transaction" (puerto 6543)
        'DISABLE_SERVER_SIDE_CURSORS': config('DB_DISABLE_SERVER_SIDE_CURSORS', default=ON_VERCEL, cast=bool),
    }
}

# ══════════════════════════════════════════════════════════════
# 7. AUTENTICACIÓN, ROLES Y CONTRASEÑAS
# ══════════════════════════════════════════════════════════════
AUTH_USER_MODEL = 'usuarios.Usuario'

AUTHENTICATION_BACKENDS = [
    # Login por correo o username; exige pertenecer a una institución activa
    'usuarios.backends.PerfilModelBackend',
    # Respaldo estándar (necesario para el /admin con superusuario)
    'django.contrib.auth.backends.ModelBackend',
]

LOGIN_URL = 'usuarios:login'
LOGIN_REDIRECT_URL = 'usuarios:home'
LOGOUT_REDIRECT_URL = 'usuarios:login'

# Hashing de contraseñas: Argon2 (requiere `pip install argon2-cffi`) con PBKDF2 de respaldo.
# NO usar SHA-256 simple para contraseñas.
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 10},
    },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Nombre que verá el usuario en su app autenticadora (Google Authenticator, etc.)
OTP_TOTP_ISSUER = 'TesisTrack'

# ══════════════════════════════════════════════════════════════
# 8. INTERNACIONALIZACIÓN
# ══════════════════════════════════════════════════════════════
LANGUAGE_CODE = 'es-pe'
TIME_ZONE = 'America/Lima'
USE_I18N = True
USE_TZ = True

# ══════════════════════════════════════════════════════════════
# 9. ARCHIVOS ESTÁTICOS Y MULTIMEDIA
#    - Estáticos: Vercel ejecuta collectstatic en el build y los sirve por su CDN
#      (Whitenoise sigue activo en local y como respaldo)
#    - Media (PDFs, logos): Cloudinary, porque el disco de Vercel es de solo lectura/efímero
# ══════════════════════════════════════════════════════════════
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Solo incluir si existe la carpeta (evita el warning staticfiles.W004)
_static_dir = BASE_DIR / 'static'
STATICFILES_DIRS = [_static_dir] if _static_dir.exists() else []

MEDIA_URL = '/media/'

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY': config('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': config('CLOUDINARY_API_SECRET', default=''),
}

STORAGES = {
    # Los PDF se guardan como recursos "raw" en Cloudinary
    'default': {
        'BACKEND': 'cloudinary_storage.storage.RawMediaCloudinaryStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

CLOUDINARY_CONFIGURADO = all(CLOUDINARY_STORAGE.values())

if CLOUDINARY_CONFIGURADO:
    STORAGES['default'] = {'BACKEND': 'cloudinary_storage.storage.RawMediaCloudinaryStorage'}
else:
    if ON_VERCEL:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured(
            'Faltan CLOUDINARY_CLOUD_NAME / CLOUDINARY_API_KEY / CLOUDINARY_API_SECRET: '
            'en Vercel no hay disco persistente para guardar los PDF.'
        )
    STORAGES['default'] = {'BACKEND': 'django.core.files.storage.FileSystemStorage'}
    MEDIA_ROOT = BASE_DIR / 'media'

# Límites de subida de entregables (validar también en el formulario).
# Vercel Functions rechaza cuerpos de petición > 4.5 MB (413): por eso 4 MB por defecto allí.
MAX_UPLOAD_SIZE_MB = config('MAX_UPLOAD_SIZE_MB', default=4 if ON_VERCEL else 10, cast=int)
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE_MB * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# ══════════════════════════════════════════════════════════════
# 10. INTEGRACIONES EXTERNAS (capa de servicios y automatización)
# ══════════════════════════════════════════════════════════════
# Correos transaccionales (Resend o Brevo, vía HTTP/REST)
EMAIL_PROVIDER = config('EMAIL_PROVIDER', default='resend')  # 'resend' | 'brevo'
RESEND_API_KEY = config('RESEND_API_KEY', default='')
BREVO_API_KEY = config('BREVO_API_KEY', default='')
EMAIL_FROM = config('EMAIL_FROM', default='TesisTrack <no-reply@tesistrack.app>')

# Cron-job.org: el endpoint /cron/alertas/ debe validar este token en el header
CRON_TOKEN = config('CRON_TOKEN', default='')

# QuickChart: generación de QR de verificación de constancias
QUICKCHART_QR_URL = config('QUICKCHART_QR_URL', default='https://quickchart.io/qr')

# Timeout para llamadas HTTP a servicios de terceros (segundos)
EXTERNAL_API_TIMEOUT = config('EXTERNAL_API_TIMEOUT', default=10, cast=int)

# URL pública base (para armar enlaces en correos y QR)
_prod_host = config('VERCEL_PROJECT_PRODUCTION_URL', default='')
SITE_URL = config('SITE_URL', default=f'https://{_prod_host}' if _prod_host else 'http://localhost:8000')

# Correos de Django (p. ej. recuperación de contraseña): por la API HTTP (Resend/Brevo).
# En desarrollo, si no hay API key, salen por consola.
_hay_api_key = bool(RESEND_API_KEY or BREVO_API_KEY)
if _hay_api_key or not DEBUG:
    EMAIL_BACKEND = 'core.email_backend.ApiEmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

PASSWORD_RESET_TIMEOUT = 60 * 60 * 3  # enlace de recuperación válido 3 horas

# ══════════════════════════════════════════════════════════════
# 11. SEGURIDAD EN PRODUCCIÓN (se activa cuando DEBUG=False)
# ══════════════════════════════════════════════════════════════
if not DEBUG:
    # Vercel termina TLS en su borde y reenvía X-Forwarded-Proto a la función
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    SECURE_HSTS_SECONDS = 31536000          # 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
    X_FRAME_OPTIONS = 'DENY'

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 60 * 60 * 8            # 8 horas
SESSION_SAVE_EVERY_REQUEST = False

# ══════════════════════════════════════════════════════════════
# 12. LOGGING (Vercel captura stdout/stderr en Runtime Logs)
# ══════════════════════════════════════════════════════════════
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': config('LOG_LEVEL', default='INFO'),
    },
    'loggers': {
        'django.security': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# ══════════════════════════════════════════════════════════════
# 13. OTROS
# ══════════════════════════════════════════════════════════════
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'