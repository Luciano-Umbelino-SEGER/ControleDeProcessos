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
BASE_DIR = Path(__file__).resolve().parent.parent

DJANGO_ENV = os.getenv("DJANGO_ENV", "").strip().lower()

AMBIENTES_PERMITIDOS = ("dev", "homolog")

if DJANGO_ENV not in AMBIENTES_PERMITIDOS:
    raise RuntimeError(
        f"DJANGO_ENV inválido: '{DJANGO_ENV}'. "
        f"Utilize um dos ambientes: {', '.join(AMBIENTES_PERMITIDOS)}."
    )

ENV_FILE = BASE_DIR / f".env.{DJANGO_ENV}"

if not ENV_FILE.is_file():
    raise RuntimeError(
        f"Arquivo de ambiente não encontrado: {ENV_FILE}"
    )

load_dotenv(ENV_FILE, override=True)

# Garante consistência entre o ambiente selecionado
# pelo processo e o declarado no arquivo .env.
if os.getenv("DJANGO_ENV", "").strip().lower() != DJANGO_ENV:
    raise RuntimeError(
        f"O DJANGO_ENV definido no arquivo {ENV_FILE.name} "
        f"não corresponde ao ambiente selecionado."
    )

CURRENT_ENV_FILE = str(ENV_FILE)

# =========================
# Debug ambiente
# =========================
logger = logging.getLogger(__name__)
logger.info(f"Ambiente carregado: {CURRENT_ENV_FILE}")

# =========================
# Configurações base
# =========================
DEBUG = env_bool("DEBUG", default=(DJANGO_ENV == "dev"))

SECRET_KEY = os.getenv("SECRET_KEY", "").strip()

if not SECRET_KEY:
    raise RuntimeError(
        f"SECRET_KEY não definida no arquivo {ENV_FILE.name}."
    )

# URL base obrigatória, definida exclusivamente no .env.
SITE_URL = os.getenv("SITE_URL", "").strip()

if not SITE_URL:
    raise RuntimeError(
        f"SITE_URL não definida no arquivo {ENV_FILE.name}."
    )

parsed = urlparse(SITE_URL)

if not parsed.scheme or not parsed.hostname:
    raise RuntimeError(
        f"SITE_URL inválida no arquivo {ENV_FILE.name}: {SITE_URL}"
    )

# ALLOWED_HOSTS
default_allowed = ["127.0.0.1", "localhost"]

if parsed.hostname and parsed.hostname not in default_allowed:
    default_allowed.append(parsed.hostname)

ALLOWED_HOSTS = env_list(
    "ALLOWED_HOSTS",
    default=default_allowed
)

# CSRF_TRUSTED_ORIGINS
def _origin_from_url(url):
    parsed_url = urlparse(url)

    if not parsed_url.scheme or not parsed_url.hostname:
        return None

    return f"{parsed_url.scheme}://{parsed_url.netloc}"


origin_from_site = _origin_from_url(SITE_URL)

csrf_defaults = (
    [origin_from_site]
    if origin_from_site
    else []
)

CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    default=csrf_defaults
)

# Cookies
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "sessionid")
CSRF_COOKIE_NAME = os.getenv("CSRF_COOKIE_NAME", "csrftoken")

# Regras extras de segurança
SESSION_COOKIE_SECURE = env_bool(
    "SESSION_COOKIE_SECURE",
    default=False
)

CSRF_COOKIE_SECURE = env_bool(
    "CSRF_COOKIE_SECURE",
    default=False
)

SECURE_SSL_REDIRECT = env_bool(
    "SECURE_SSL_REDIRECT",
    default=False
)

SECURE_HSTS_SECONDS = env_int(
    "SECURE_HSTS_SECONDS",
    default=0
)

SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=False
)

SECURE_HSTS_PRELOAD = env_bool(
    "SECURE_HSTS_PRELOAD",
    default=False
)

# Sessões no banco
SESSION_ENGINE = "django.contrib.sessions.backends.db"

# Prefixo de cache por ambiente
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
    "auditoria.apps.AuditoriaConfig",

    "crispy_forms",
    "crispy_bootstrap5",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "arquiteturaprocessos.middleware.ForceLogoutOnPasswordResetMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "auditoria.middleware.AuditoriaMiddleware",
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
                "arquiteturaprocessos.context_processors.permissoes_menu",
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
STATICFILES_DIRS = [BASE_DIR / "static"]

STATIC_ROOT = Path(os.getenv("STATIC_ROOT", "staticfiles"))

if not STATIC_ROOT.is_absolute():
    STATIC_ROOT = BASE_DIR / STATIC_ROOT

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_REDIRECT_URL = "arquiteturaprocessos:arquiteturaprocessos"
LOGIN_URL = "arquiteturaprocessos:fazer_login"
LOGOUT_REDIRECT_URL = "arquiteturaprocessos:homepage"

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

# ----------------------------------------
# 🔥 CACHE (controle de tentativas de login)
# ----------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "sigemp-cache",
    }
}

