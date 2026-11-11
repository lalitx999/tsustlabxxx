"""Developer machine settings."""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True
ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# Without Redis running locally, set CELERY_TASK_ALWAYS_EAGER=true in .env so
# tasks run inline. Production always uses a real worker.
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
