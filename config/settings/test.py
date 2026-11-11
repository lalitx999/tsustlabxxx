"""Test settings: tasks run inline, mail is captured in memory."""
from .base import *  # noqa: F401,F403

DEBUG = False
CELERY_TASK_ALWAYS_EAGER = True
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
PROMPTPAY_RECEIVER_ID = '0105569150179'

# Uploaded slips/photos and generated PDFs go to a throw-away folder, not ./media.
import tempfile  # noqa: E402
from pathlib import Path  # noqa: E402

MEDIA_ROOT = Path(tempfile.mkdtemp(prefix='trustlabx-test-media-'))

# Tests must never reach LINE / WeChat, whatever the developer's .env contains.
LINE_CHANNEL_ACCESS_TOKEN = ''
LINE_GROUP_ID = ''
WECHAT_WORK_WEBHOOK_URL = ''
THAI_FONT_PATH = ''
