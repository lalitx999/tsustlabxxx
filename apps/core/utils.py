"""Small parsing helpers shared by services."""
import base64
import binascii
import uuid

from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError

from .exceptions import ServiceError

MAX_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = {'JPEG': 'jpg', 'PNG': 'png', 'WEBP': 'webp', 'GIF': 'gif'}


def parse_pk(value) -> int:
    """Accept legacy display ids such as 'BK-0012' or 'TL2609-1-0012'."""
    try:
        return int(str(value).strip().split('-')[-1])
    except (ValueError, AttributeError):
        raise ServiceError('รหัสรายการไม่ถูกต้อง')


def clean_text(value, max_length=None) -> str:
    text = str(value or '').strip()
    if max_length and len(text) > max_length:
        raise ServiceError(f'ข้อความยาวเกิน {max_length} ตัวอักษร')
    return text


def digits_only(value) -> str:
    return ''.join(ch for ch in str(value or '') if ch.isdigit())


def decode_image(data_url: str) -> ContentFile:
    """Validate a base64 image (data URL or raw) and return a Django file.

    Pillow verifies the bytes really are an image of an allowed type.
    """
    if not isinstance(data_url, str) or not data_url:
        raise ServiceError('ไฟล์รูปภาพไม่ถูกต้อง')
    raw = data_url.split(',', 1)[1] if data_url.startswith('data:') else data_url
    if len(raw) > MAX_IMAGE_BYTES * 4 // 3 + 4:
        raise ServiceError('ภาพต้องมีขนาดไม่เกิน 8 MB')
    try:
        content = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        raise ServiceError('ไฟล์รูปภาพไม่ถูกต้องหรือเสียหาย')
    try:
        from io import BytesIO
        with Image.open(BytesIO(content)) as img:
            fmt = img.format
            img.verify()
    except (UnidentifiedImageError, OSError):
        raise ServiceError('ไฟล์รูปภาพไม่ถูกต้องหรือเสียหาย')
    if fmt not in ALLOWED_IMAGE_FORMATS:
        raise ServiceError('รองรับเฉพาะไฟล์ JPG, PNG, WEBP หรือ GIF')
    return ContentFile(content, name=f'{uuid.uuid4().hex}.{ALLOWED_IMAGE_FORMATS[fmt]}')
