# TesisTrack

SaaS multi-tenant para el seguimiento de proyectos integradores (Django 5, PostgreSQL, Cloudinary, Brevo/Resend, Vercel).

## Requisitos
- Python 3.11 o 3.12
- Git
- PostgreSQL local (opcional: también puedes usar directamente Supabase)
- Cuenta gratuita en Cloudinary (para guardar los PDF)

## 1. Clonar e instalar (Windows, PowerShell)

```powershell
git clone https://github.com/AldoVasquez07/cc-proy-final-2026-b.git
cd cc-proy-final-2026-b
py -m venv env
env\Scripts\activate
pip install -r requirements.txt
```

## 2. Configurar variables de entorno

Crea un archivo `.env` en la raíz (junto a `manage.py`). **Nunca lo subas a GitHub.**

```env
SECRET_KEY=genera_una_clave_con_el_comando_de_abajo
DEBUG=True
SITE_URL=http://localhost:8000

# Base de datos
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=tu_contraseña
DB_HOST=localhost
DB_PORT=5432
DB_SSLMODE=prefer

# Cloudinary (PDF de entregas)
CLOUDINARY_CLOUD_NAME=tu_cloud_name
CLOUDINARY_API_KEY=tu_api_key
CLOUDINARY_API_SECRET=tu_api_secret

# Correos (Brevo)
EMAIL_PROVIDER=brevo
BREVO_API_KEY=
EMAIL_FROM=TesisTrack <tu_correo_verificado@gmail.com>

# Alertas programadas
CRON_TOKEN=genera_un_token_con_el_comando_de_abajo
MAX_UPLOAD_SIZE_MB=10
```

Generar `SECRET_KEY` y `CRON_TOKEN`:

```powershell
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
python -c "import secrets; print(secrets.token_urlsafe(40))"
```

### Opciones de base de datos
- **PostgreSQL local:** crea la base con `psql -U postgres -c "CREATE DATABASE tesistrack;"` y usa `DB_NAME=tesistrack`, `DB_HOST=localhost`, `DB_SSLMODE=prefer`.
- **Supabase (pooler):** usa los datos de *Connect → Connection pooling*:
  `DB_HOST=aws-1-us-east-1.pooler.supabase.com`, `DB_USER=postgres.<project-ref>`, `DB_NAME=postgres`, `DB_SSLMODE=require`, `DB_PORT=5432` (modo sesión, para local y migraciones).

### Notas
- Sin claves de Cloudinary, en local los PDF se guardan en la carpeta `media/`.
- Sin `BREVO_API_KEY` ni `RESEND_API_KEY`, con `DEBUG=True` los correos salen por la **consola** donde corre el servidor.

## 3. Crear tablas y superusuario

```powershell
python manage.py migrate
python manage.py createsuperuser
```

## 4. Ejecutar

```powershell
python manage.py runserver
```

Abre **http://127.0.0.1:8000/** (con `http://`, sin `s`).

| Ruta | Descripción |
|---|---|
| `/` | Página de inicio |
| `/registro/` | Registro de una institución (crea el Coordinador) |
| `/login/` | Inicio de sesión |
| `/repositorio/` | Repositorio público de proyectos aprobados |
| `/password/recuperar/` | Recuperación de contraseña |
| `/verificar/<uuid>/` | Verificación pública de una constancia |
| `/admin/` | Administración de Django (superusuario) |

## 5. Probar el flujo completo
1. Entra a `/registro/` y registra una institución. Se crea el Coordinador.
2. Configura el 2FA: escanea el QR con Google Authenticator (o similar) e ingresa el código de 6 dígitos. Guarda los códigos de respaldo.
3. Como Coordinador, crea **carreras** y un **periodo académico** activo.
4. Crea un **docente** y un **estudiante**.
5. Crea un **proyecto** y asígnalo a ambos.
6. Como Docente, crea los **hitos** con fecha límite.
7. Como Estudiante, **entrega un PDF** de cada hito.
8. Como Docente, **revisa** (observar o aprobar) cada entrega con nota de 0 a 20.
9. Al aprobar todos los hitos, el proyecto pasa a **COMPLETADO** y se emite la **constancia** con QR.
10. Como Coordinador, **publica** el proyecto en el repositorio público.

Cada rol inicia sesión en una sesión distinta: usa una ventana de incógnito o un navegador diferente para alternar entre ellos.

## 6. Pruebas automatizadas

Las pruebas crean una base temporal `test_<nombre>`. **No las ejecutes con el `.env` apuntando a Supabase.** Usa tu PostgreSQL local:

```powershell
$env:DB_NAME="tesistrack"
$env:DB_USER="postgres"
$env:DB_PASSWORD="tu_contraseña_local"
$env:DB_HOST="localhost"
$env:DB_PORT="5432"
$env:DB_SSLMODE="prefer"
python manage.py test
```

Las variables de la sesión de PowerShell tienen prioridad sobre el `.env` y se borran al cerrar la terminal.

## 7. Prueba de carga (opcional)

```powershell
pip install locust
locust -f locustfile.py --host http://127.0.0.1:8000
```
Abre http://localhost:8089 para configurar usuarios y ejecutar.

## 8. Alertas de vencimiento (opcional en local)

```powershell
curl.exe -H "X-Cron-Token: TU_CRON_TOKEN" http://127.0.0.1:8000/cron/alertas/
```
Responde un JSON con el número de recordatorios enviados. Sin token responde 403.

## 9. Problemas frecuentes

| Problema | Solución |
|---|---|
| `ERR_SSL_PROTOCOL_ERROR` o redirige a `https` | Usa `http://127.0.0.1:8000/`. Con `DEBUG=False` el servidor fuerza HTTPS y el navegador lo recuerda: borra HSTS en `chrome://net-internals/#hsts` (dominio `localhost`) o prueba otro puerto (`runserver 8001`). |
| `Invalid cloud_name` al subir PDF | `CLOUDINARY_CLOUD_NAME` debe ser el nombre de la cuenta (Cloudinary → Settings → API Keys, etiqueta "Cloud name"). |
| `No module named 'argon2'` | `pip install -r requirements.txt` (incluye `argon2-cffi`). |
| `server closed the connection unexpectedly` en `migrate` con Supabase | Vuelve a ejecutar `python manage.py migrate`. Si persiste, usa `DB_PORT=6543` y `DB_DISABLE_SERVER_SIDE_CURSORS=True`. |
| `password authentication failed` | Revisa `DB_USER` (en Supabase lleva el ID: `postgres.<project-ref>`) y `DB_PASSWORD`. |
| No llegan los correos | Verifica el remitente en Brevo, que `EMAIL_FROM` use ese mismo correo, y revisa spam. |
| PDF rechazado por tamaño | Límite definido por `MAX_UPLOAD_SIZE_MB` (4 en Vercel por su tope de 4.5 MB por petición). |

## 10. Despliegue (resumen)
Vercel (aplicación) + Supabase (PostgreSQL) + Cloudinary (archivos) + GitHub Actions (CI y migraciones) + Cron-job.org (alertas).

En Vercel configura las mismas variables del `.env`, pero con estos cambios:

```env
DEBUG=False
SITE_URL=https://TU-PROYECTO.vercel.app
DB_PORT=6543
DB_DISABLE_SERVER_SIDE_CURSORS=True
DB_CONN_MAX_AGE=0
MAX_UPLOAD_SIZE_MB=4
```

En GitHub (Settings → Secrets and variables → Actions) crea: `SECRET_KEY`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` (con `5432`). Cada push a `main` ejecuta las pruebas, aplica las migraciones y Vercel despliega.

En Cron-job.org crea un job `GET https://TU-PROYECTO.vercel.app/cron/alertas/` con el header `X-Cron-Token: <CRON_TOKEN>`, cada hora.

## Estructura
```
tesistrack/   configuración (settings, urls, wsgi)
core/         instituciones, carreras, periodos, landing
usuarios/     autenticación, roles, 2FA, recuperación de contraseña
proyectos/    proyectos, hitos, entregas, revisiones, constancias, cron
analitica/    paneles con Chart.js
templates/    plantillas Bootstrap 5
```

## Seguridad
Contraseñas con Argon2, 2FA TOTP, aislamiento por institución en cada consulta, 404 ante datos de otra institución, HTTPS/HSTS en producción y token comparado en tiempo constante en el endpoint de cron.
