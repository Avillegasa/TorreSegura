import os
from pathlib import Path
from datetime import timedelta
import environ
import socket

hostname = socket.gethostname()

BASE_DIR = Path(__file__).resolve().parent.parent

# Configuración de environ con valores por defecto
env = environ.Env(
    DEBUG=(bool, False),
    USE_LOCAL_DB=(bool, False),
)

# Leer archivo .env si existe
environ.Env.read_env(env_file=os.path.join(BASE_DIR, '.env')) 

# Secreto dedicado para firmar QRs (opcional). Si no se define, se usa SECRET_KEY como fallback.
QR_SECRET_KEY = env('QR_SECRET_KEY', default=None)

# ─── BNB Payment Gateway (QR Simple) ─────────────────────────────────
BNB_SANDBOX = env.bool('BNB_SANDBOX', default=True)
BNB_ACCOUNT_ID = env('BNB_ACCOUNT_ID', default='')
BNB_AUTHORIZATION_ID = env('BNB_AUTHORIZATION_ID', default='')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    '.railway.app', 
]
if os.environ.get('RAILWAY_PUBLIC_DOMAIN'):
    ALLOWED_HOSTS.append(os.environ.get('RAILWAY_PUBLIC_DOMAIN'))

ALLOWED_HOSTS = [host for host in ALLOWED_HOSTS if host]

# En desarrollo, permitir acceso por IP local/LAN (evita DisallowedHost al entrar por 192.168.x.x)
if DEBUG and '*' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('*')

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'whitenoise.runserver_nostatic',  # Para servir archivos estáticos en desarrollo
    'django.contrib.sites',  # Necesario para django-allauth
    'django_extensions',
    

    'crispy_forms',
    'crispy_bootstrap4',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',  # Para JWT
    'rest_framework.authtoken',  # Para autenticación con token
    # Apps propias
    'usuarios',
    'viviendas',
    'accesos',
    'personal',
    'financiero',
    'reportes',
    'alertas',
    'areas_comunes',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Debe ser el primero
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Middleware para servir archivos estáticos
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',  # Middleware de AllAuth 
    'condominio_app.middleware.force_password_change.ForcePasswordChangeMiddleware',
]

ROOT_URLCONF = 'condominio_app.urls'

# ============ CONFIGURACIÓN DE CORS Y CSRF ============
if DEBUG:
    # Para desarrollo - permitir cualquier origen
    CORS_ALLOW_ALL_ORIGINS = True
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8080",
    ]
    
    # CSRF para desarrollo
    CSRF_TRUSTED_ORIGINS = [
        'http://localhost:8000',
        'http://127.0.0.1:8000',
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        "https://torresegura.up.railway.app"
    ]
else:
    # Para producción - orígenes específicos
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = [
        "https://pilinmaster-production.up.railway.app",
    ]
    
    # CSRF para producción
    CSRF_TRUSTED_ORIGINS = [
        'https://pilinmaster-production.up.railway.app',
        'https://*.railway.app',
    ]

CORS_ALLOW_CREDENTIALS = True

# Headers permitidos
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
# Métodos HTTP permitidos
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'usuarios.context_processors.clientes_potenciales_count',
            ],
        },
    },
]

WSGI_APPLICATION = 'condominio_app.wsgi.application'

# ============ CONFIGURACIÓN DE BASE DE DATOS ============
# Usar SQLite para desarrollo local si USE_LOCAL_DB=True, cambiar el valor tanto en el env como en las variables de railway
USE_LOCAL_DB = env.bool('USE_LOCAL_DB', default=DEBUG)

if USE_LOCAL_DB:
    print("Usando SQLite para desarrollo local")
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    import dj_database_url
    print("Usando PostgreSQL para produccion")
    database_url = env('DATABASE_URL', default=None)
    if not database_url:
        raise ValueError(
            "DATABASE_URL no está configurado. Define DATABASE_URL o activa USE_LOCAL_DB=True para usar SQLite."
        )
    DATABASES = {
        "default": dj_database_url.config(
            default=database_url,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/
LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'America/La_Paz'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

# Media files
MEDIA_URL = '/mediafiles/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'mediafiles')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# User model personalizado
AUTH_USER_MODEL = 'usuarios.Usuario'

# Configuración de login
LOGIN_REDIRECT_URL = 'dashboard'
LOGIN_URL = 'login'
LOGOUT_REDIRECT_URL = 'login'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap4"
CRISPY_TEMPLATE_PACK = "bootstrap4"

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '30/minute',
        'user': '120/minute',
    },
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}

# Security settings for production
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# ====== CONFIGURACIÓN DE LOGGING ======
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'corsheaders': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG and USE_LOCAL_DB else 'INFO',
        },
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Django AllAuth configuración
AUTHENTICATION_BACKENDS = [
    # Needed to login by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',

    # `allauth` specific authentication methods, such as login by e-mail
    'allauth.account.auth_backends.AuthenticationBackend',
]
SITE_ID = 1

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = True
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_AUTHENTICATION_METHOD = 'username_email'
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGIN_ON_GET = False

ACCOUNT_CONFIRM_EMAIL_ON_GET = True

# Configuración de Email
EMAIL_BACKEND = env('EMAIL_BACKEND', default='')
if not EMAIL_BACKEND:
    EMAIL_BACKEND = (
        'django.core.mail.backends.console.EmailBackend'
        if DEBUG
        else 'django.core.mail.backends.smtp.EmailBackend'
    )
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='Sistema <no-reply@dominio.com>')

# Configuración de redes sociales
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'OAUTH_PKCE_ENABLED': True,
    }
}

SOCIALACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_ADAPTER = 'usuarios.adapters.CustomSocialAccountAdapter'
ACCOUNT_ADAPTER = 'usuarios.adapters.CustomAccountAdapter'

# Credenciales Google opcionales (evitar hardcodear valores)
GOOGLE_CLIENT_ID = env('GOOGLE_CLIENT_ID', default='')
GOOGLE_SECRET = env('GOOGLE_SECRET', default='')

# Notificaciones con mensajes
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
