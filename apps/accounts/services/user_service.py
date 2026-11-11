"""Staff account management (admin only)."""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from apps.core.exceptions import ServiceError
from apps.core.permissions import STAFF_ROLES
from apps.core.utils import clean_text


def _password(password, user):
    try:
        validate_password(password, user)
    except DjangoValidationError as exc:
        raise ServiceError(' '.join(exc.messages))


@transaction.atomic
def save_staff(data: dict, user=None):
    User = get_user_model()
    creating = user is None
    username = clean_text(data.get('username'), 150)
    if creating and not username:
        raise ServiceError('กรุณาระบุชื่อผู้ใช้')
    if username and User.objects.filter(username=username).exclude(pk=getattr(user, 'pk', None)).exists():
        raise ServiceError('ชื่อผู้ใช้นี้ถูกใช้แล้ว')
    role = data.get('role', getattr(user, 'role', 'front'))
    if role not in STAFF_ROLES:
        raise ServiceError('บทบาทไม่ถูกต้อง')
    user = user or User(username=username)
    if username:
        user.username = username
    user.role = role
    user.full_name = clean_text(data.get('full_name', user.full_name), 100)
    user.email = clean_text(data.get('email', user.email), 254)
    user.phone = clean_text(data.get('phone', user.phone or ''), 20) or None
    if 'is_active' in data:
        user.is_active = bool(data['is_active'])
    password = data.get('password')
    if creating and not password:
        raise ServiceError('กรุณาตั้งรหัสผ่าน')
    if password:
        _password(password, user)
        user.set_password(password)
    user.save()
    return user


def delete_staff(user, actor) -> None:
    if user.pk == actor.pk:
        raise ServiceError('ไม่สามารถลบบัญชีของตัวเองได้')
    # Staff appear in audit history, so deactivate instead of deleting rows.
    user.is_active = False
    user.save(update_fields=['is_active'])
