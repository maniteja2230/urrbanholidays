"""
Urban Holidays Django Settings
Handles: local dev  |  ngrok  |  Railway/Render production
"""

import os
import dj_database_url
from pathlib import Path
from decouple import config, Csv

# ── Paths ─────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ── Security ──────────────────────────────────────────────────────────────
SECRET_KEY = config(
    'SECRET_KEY',
    default='django-insecure-change-me-in-production-urbanholidays-2024'
)
DEBUG = config('DEBUG', default=False, cast=bool)

# Accept all hosts — Railway/Render assigns dynamic subdomains
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='*',
    cast=Csv()
)

# ── ngrok / Reverse-Proxy / Railway Support ───────────────────────────────
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://localhost:8080',
    'http://127.0.0.1:8000',
    # ngrok
    'https://*.ngrok.io',
    'https://*.ngrok-free.app',
    'https://*.ngrok.app',
    # Railway / Render custom domains
    'https://*.railway.app',
    'https://*.up.railway.app',
    'https://*.onrender.com',
]

# Add SITE_URL to trusted origins if set (your custom domain)
_site_url = config('SITE_URL', default='')
if _site_url and _site_url not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(_site_url)

# ── Installed Apps ────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Third-party
    'crispy_forms',
    'crispy_bootstrap5',
    'whitenoise.runserver_nostatic',

    # Local apps
    'core.apps.CoreConfig',
    'accounts.apps.AccountsConfig',
    'vouchers.apps.VouchersConfig',
    'packages.apps.PackagesConfig',
    'payments.apps.PaymentsConfig',
    'dashboard.apps.DashboardConfig',
    'notifications.apps.NotificationsConfig',
]

# ── Middleware ────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'urbanholidays.urls'

# ── Templates ─────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.site_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'urbanholidays.wsgi.application'

# ── Database ──────────────────────────────────────────────────────────────
# If DATABASE_URL is set (Railway/Render inject this automatically),
# use PostgreSQL. Otherwise fall back to local SQLite for development.
DATABASE_URL = config('DATABASE_URL', default='')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ── Password Validation ───────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internationalisation ──────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Asia/Kolkata'
USE_I18N = True
USE_TZ   = True

# ── Static & Media Files ──────────────────────────────────────────────────
STATIC_URL       = '/static/'
STATIC_ROOT      = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# WhiteNoise serves static files efficiently in production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Auth ──────────────────────────────────────────────────────────────────
AUTH_USER_MODEL     = 'auth.User'
LOGIN_URL           = '/accounts/login/'
LOGIN_REDIRECT_URL  = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# ── Crispy Forms ──────────────────────────────────────────────────────────
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK          = 'bootstrap5'

# ── Email ─────────────────────────────────────────────────────────────────
EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = config('EMAIL_HOST',          default='smtp.gmail.com')
EMAIL_PORT          = config('EMAIL_PORT',          default=587, cast=int)
EMAIL_HOST_USER     = config('EMAIL_HOST_USER',     default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS       = config('EMAIL_USE_TLS',       default=True, cast=bool)
DEFAULT_FROM_EMAIL  = config(
    'DEFAULT_FROM_EMAIL',
    default='Urban Holidays <noreply@urbanholidays.com>'
)

# ── Razorpay ──────────────────────────────────────────────────────────────
RAZORPAY_KEY_ID     = config('RAZORPAY_KEY_ID',     default='')
RAZORPAY_KEY_SECRET = config('RAZORPAY_KEY_SECRET', default='')

# ── Site / Business Settings ──────────────────────────────────────────────
SITE_NAME             = config('SITE_NAME',             default='Urban Holidays')
SITE_URL              = config('SITE_URL',              default='https://yoursite.railway.app')
VOUCHER_PRICE         = config('VOUCHER_PRICE',         default=149,  cast=int)
VOUCHER_VALIDITY_DAYS = config('VOUCHER_VALIDITY_DAYS', default=365,  cast=int)
REFERRAL_BONUS        = config('REFERRAL_BONUS',        default=50,   cast=int)

# ── Session ───────────────────────────────────────────────────────────────
SESSION_COOKIE_AGE         = 86400 * 30   # 30 days
SESSION_SAVE_EVERY_REQUEST = True

# ── Production Security (auto-enabled when DEBUG=False) ───────────────────
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER      = True
    SECURE_CONTENT_TYPE_NOSNIFF    = True
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_SECONDS            = 31536000
    SECURE_SSL_REDIRECT            = False  # Railway handles SSL termination
    SESSION_COOKIE_SECURE          = True
    CSRF_COOKIE_SECURE             = True
    X_FRAME_OPTIONS                = 'DENY'

# ── Logging ───────────────────────────────────────────────────────────────
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO' if DEBUG else 'WARNING',
            'propagate': True,
        },
    },
}
