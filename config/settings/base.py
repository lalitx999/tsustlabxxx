"""Settings shared by every environment.

Secrets and anything that differs per host come from environment variables
(.env via django-environ). Nothing secret is hard-coded here.
"""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env', overwrite=False)

SECRET_KEY = env('DJANGO_SECRET_KEY')
DEBUG = False
ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS', default=[])
CSRF_TRUSTED_ORIGINS = env.list('DJANGO_CSRF_TRUSTED_ORIGINS', default=[])
SITE_URL = env('SITE_URL', default='http://localhost:8000').rstrip('/')

INSTALLED_APPS = [
    'django.contrib.admin',          # superuser-only maintenance; staff use apps.backoffice
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    'apps.core',
    'apps.accounts',
    'apps.catalog',
    'apps.customers',
    'apps.bookings',
    'apps.inspections',
    'apps.inquiries',
    'apps.notifications',
    'apps.audit',
    'apps.reports',
    'apps.website',
    'apps.backoffice',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.core.middleware.LanguageMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

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
                'apps.core.context_processors.site',
                'apps.backoffice.context_processors.backoffice',
            ],
        },
    },
]

DATABASES = {
    # e.g. postgres://user:password@localhost:5432/trustlab
    'default': env.db('DATABASE_URL'),
}
DATABASES['default']['CONN_MAX_AGE'] = env.int('DB_CONN_MAX_AGE', default=60)
DATABASES['default']['CONN_HEALTH_CHECKS'] = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.StaffUser'
LOGIN_URL = 'accounts:staff_login'
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
]

LANGUAGE_CODE = 'th'
TIME_ZONE = 'Asia/Bangkok'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = Path(env('MEDIA_ROOT', default=str(BASE_DIR / 'media')))

# Base64 photos from the camera pages can be several MB each.
DATA_UPLOAD_MAX_MEMORY_SIZE = 45 * 1024 * 1024

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 60 * 60 * 12
CSRF_COOKIE_HTTPONLY = False  # Ajax helper reads the token from the cookie.

# --- Celery (long-running work: e-mail, PDF, LINE/WeChat, EasySlip) ---
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default=None)
CELERY_TASK_ALWAYS_EAGER = env.bool('CELERY_TASK_ALWAYS_EAGER', default=False)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_TIME_LIMIT = 120
CELERY_TASK_SOFT_TIME_LIMIT = 100
CELERY_TIMEZONE = TIME_ZONE
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

# --- E-mail ---
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_PORT = env.int('EMAIL_PORT', default=465)
EMAIL_USE_SSL = env.bool('EMAIL_USE_SSL', default=True)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=False)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='TRUST LAB THAILAND <no-reply@trustlabthailand.com>')
EMAIL_TIMEOUT = 20

# --- Business / integrations ---
PROMPTPAY_RECEIVER_ID = env('PROMPTPAY_RECEIVER_ID', default='')
PAYMENT_BANK_NAME = env('PAYMENT_BANK_NAME', default='')
PAYMENT_ACCOUNT_NAME = env('PAYMENT_ACCOUNT_NAME', default='')
PAYMENT_ACCOUNT_NUMBER = env('PAYMENT_ACCOUNT_NUMBER', default='')
EASYSLIP_API_KEY = env('EASYSLIP_API_KEY', default='')
LINE_CHANNEL_ID = env('LINE_CHANNEL_ID', default='')
LINE_CHANNEL_SECRET = env('LINE_CHANNEL_SECRET', default='')
LINE_CHANNEL_ACCESS_TOKEN = env('LINE_CHANNEL_ACCESS_TOKEN', default='')
LINE_GROUP_ID = env('LINE_GROUP_ID', default='')
WECHAT_WORK_WEBHOOK_URL = env('WECHAT_WORK_WEBHOOK_URL', default='')
THAI_FONT_PATH = env('THAI_FONT_PATH', default='')
# YouTube embed URL for the home-page 'Video Reviews' button (e.g. https://www.youtube.com/embed/<id>).
REVIEW_VIDEO_URL = env('REVIEW_VIDEO_URL', default='')
EXTERNAL_HTTP_TIMEOUT = 10

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'plain': {'format': '%(asctime)s %(levelname)s %(name)s %(message)s'}},
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'plain'}},
    'root': {'handlers': ['console'], 'level': env('LOG_LEVEL', default='INFO')},
}
