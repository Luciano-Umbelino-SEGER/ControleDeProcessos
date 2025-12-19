import os
from pathlib import Path
from dotenv import load_dotenv
from decouple import config

# =========================
# Paths / Ambiente (.env)
# =========================
#BASE_DIR = Path(__file__).resolve().parents[2]  # pasta raiz do projeto (onde está manage.py)
BASE_DIR = Path(__file__).resolve().parent.parent
DJANGO_ENV = os.getenv('DJANGO_ENV', 'dev')    # dev | homolog | prod

env_file = BASE_DIR / f'.env.{DJANGO_ENV}'
fallback_env = BASE_DIR / '.env'

if env_file.exists():
    load_dotenv(env_file)
    CURRENT_ENV_FILE = str(env_file)
else:
    if fallback_env.exists():
        load_dotenv(fallback_env)
        CURRENT_ENV_FILE = str(fallback_env)

# =========================
# Configs base
# =========================
SESSION_COOKIE_NAME = config('SESSION_COOKIE_NAME', default='sessionid')
CSRF_COOKIE_NAME = config('CSRF_COOKIE_NAME', default='csrftoken')
SECRET_KEY = config('SECRET_KEY', default='insecure-dev-key')
DEBUG = config('DEBUG', default=False, cast=bool)

# Rodando sem subdomínios: apenas localhost/127.0.0.1
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

# CSRF confiando nas origens por porta:
# - DEV:    127.0.0.1:8000
# - HOMOLOG:127.0.0.1:8001
CSRF_TRUSTED_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://127.0.0.1:8001',
]

# Sessões no banco (isola por DB)
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Opcional: se você usa cache, diferencie prefixo por ambiente
CACHE_KEY_PREFIX = f'controleproc_{DJANGO_ENV}'

# =========================
# Database (PostgreSQL)
# =========================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# =========================
# Apps / Middleware / Templates
# =========================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'arquiteturaprocessos',

    'crispy_forms',
    'crispy_bootstrap5',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'controleprocessos.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'controleprocessos.wsgi.application'

# =========================
# Auth
# =========================
AUTH_USER_MODEL = "arquiteturaprocessos.Usuario"
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# =========================
# i18n / timezone
# =========================
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# =========================
# Static / Media
# =========================
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR.parent / 'static',                  # <-- logo, imagens
    BASE_DIR / 'static',                          # <-- js/processos.js
]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_REDIRECT_URL = 'arquiteturaprocessos:arquiteturaprocessos'
LOGIN_URL = 'arquiteturaprocessos:fazer_login'
LOGOUT_REDIRECT_URL = 'arquiteturaprocessos:arquiteturaprocessos'

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# Email (console por padrão)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Segurança: permitir PDF em iframe no mesmo domínio
X_FRAME_OPTIONS = 'SAMEORIGIN'
