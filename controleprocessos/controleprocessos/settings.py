import os
import logging
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv

# =========================
# Funções auxiliares de env
# =========================
def env_bool(key, default=False):
    val = os.getenv(key)
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "t", "yes", "y", "on")

def env_int(key, default=None):
    val = os.getenv(key)
    if val is None or str(val).strip() == "":
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default

def env_list(key, default=None, sep=","):
    val = os.getenv(key)
    if not val:
        return default or []
    return [item.strip() for item in val.split(sep) if item.strip()]

# =========================
# Paths / Ambiente (.env)
# =========================
BASE_DIR = Path(__file__).resolve().parent.parent  # pasta raiz do projeto (onde está manage.py)

# Descobre o ambiente via variável do SO (padrão: 'dev')
DJANGO_ENV = os.getenv("DJANGO_ENV", "dev").strip().lower()  # dev | homolog | prod

# (Opcional) .env base e .env específico do ambiente
base_env = BASE_DIR / ".env"
if base_env.exists():
    load_dotenv(base_env, override=False)  # comum aos ambientes (se quiser)

env_file = BASE_DIR / f".env.{DJANGO_ENV}"
fallback_env = base_env  # já carregado acima, se existir

if env_file.exists():
    load_dotenv(env_file, override=True)  # garante a env do ambiente
    CURRENT_ENV_FILE = str(env_file)
else:
    if DJANGO_ENV == "prod":
        raise RuntimeError("Arquivo .env.prod não encontrado!")
    elif fallback_env and fallback_env.exists():
        CURRENT_ENV_FILE = str(fallback_env)
    else:
        CURRENT_ENV_FILE = "N/A"

# Prints de diagnóstico (úteis em dev/homolog)
if DJANGO_ENV != "prod":
    print(f">>> DJANGO_ENV = {DJANGO_ENV}")
    print(f">>> ENV FILE = {CURRENT_ENV_FILE}")

# =========================
# Debug ambiente
# =========================
logger = logging.getLogger(__name__)
logger.info(f"Ambiente carregado: {CURRENT_ENV_FILE}")

# =========================
# Configs base
# =========================
# Em dev, se não houver DEBUG no .env, assume True; em homolog/prod, assume False
DEBUG = env_bool("DEBUG", default=(DJANGO_ENV == "dev"))

SECRET_KEY = os.getenv("SECRET_KEY", "insecure-dev-key")

# URL base do sistema (inclui host e porta)
DEFAULT_SITE_URL = "http://127.0.0.1:8000" if DJANGO_ENV == "dev" else "http://127.0.0.1:8001"
SITE_URL = os.getenv("SITE_URL", DEFAULT_SITE_URL)

# ALLOWED_HOSTS: aceita CSV via env; se não vier, usa host do SITE_URL + localhost/127.0.0.1
parsed = urlparse(SITE_URL)
default_allowed = ["127.0.0.1", "localhost"]
if parsed.hostname and parsed.hostname not in default_allowed:
    default_allowed.append(parsed.hostname)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", default=default_allowed)

# CSRF_TRUSTED_ORIGINS: precisa esquema+host+porta
def _origin_from_url(u):
    p = urlparse(u)
    port = p.port or (80 if p.scheme == "http" else 443)
    return f"{p.scheme}://{p.hostname}:{port}" if p.hostname else None

csrf_defaults = set()
origin_from_site = _origin_from_url(SITE_URL)
if origin_from_site:
    csrf_defaults.add(origin_from_site)
# adiciona portas padrão de dev/homolog
csrf_defaults.update({
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8001",
    "http://localhost:8000",
    "http://localhost:8001",
})
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", default=list(csrf_defaults))

# Cookies
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "sessionid")
CSRF_COOKIE_NAME = os.getenv("CSRF_COOKIE_NAME", "csrftoken")

# Regras extras de segurança (ajuste via .env conforme necessário)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", default=(DJANGO_ENV == "prod"))
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", default=(DJANGO_ENV == "prod"))
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", default=(DJANGO_ENV == "prod"))
SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", default=(31536000 if DJANGO_ENV == "prod" else 0))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", default=False)

# Sessões no banco (isola por DB)
SESSION_ENGINE = "django.contrib.sessions.backends.db"

# Diferenciar prefixo de cache por ambiente (se usar cache)
CACHE_KEY_PREFIX = f"controleproc_{DJANGO_ENV}"

# =========================
# Database (PostgreSQL)
# =========================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

# =========================
# Apps / Middleware / Templates
# =========================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "arquiteturaprocessos",
    "portalseger",
    "auditoria",

    "crispy_forms",
    "crispy_bootstrap5",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "arquiteturaprocessos.middleware.ForceLogoutOnPasswordResetMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "controleprocessos.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "controleprocessos.wsgi.application"

# =========================
# Auth
# =========================
AUTH_USER_MODEL = "arquiteturaprocessos.Usuario"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# =========================
# i18n / timezone
# =========================
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# =========================
# Static / Media
# =========================
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]  # ex.: js/processos.js

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_REDIRECT_URL = "arquiteturaprocessos:arquiteturaprocessos"
LOGIN_URL = "arquiteturaprocessos:fazer_login"
LOGOUT_REDIRECT_URL = "arquiteturaprocessos:arquiteturaprocessos"

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Email
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = env_int("EMAIL_PORT", default=25) or 25
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", default=False)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", default=False)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "elpi@seger.es.gov.br")

# Segurança: permitir PDF em iframe no mesmo domínio
X_FRAME_OPTIONS = "SAMEORIGIN"

# =========================
# Logging (console)
# =========================
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "std": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "std"},
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
}