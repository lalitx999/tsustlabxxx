from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction

from apps.catalog.models import MembershipLevel
from apps.core.exceptions import ServiceError
from apps.core.utils import clean_text, digits_only
from apps.customers.models import Customer


def find_or_create_customer(*, full_name, phone, email=None, line_id=None, note='', tier='general') -> Customer:
    """Look up by phone (unique); create with the chosen membership tier if new."""
    phone = digits_only(phone)
    full_name = clean_text(full_name, 255)
    if not full_name or len(phone) < 9:
        raise ServiceError('กรุณาระบุชื่อและเบอร์โทรให้ครบ')
    customer = Customer.objects.select_related('membership_level').filter(phone_number=phone).first()
    if customer:
        return customer
    tier = (tier or 'general').strip().lower()
    level = MembershipLevel.objects.filter(level_name__iexact=tier).first()
    if level is None and tier != 'general':
        raise ServiceError('ไม่พบระดับสมาชิกที่เลือก กรุณาตรวจสอบข้อมูลสมาชิก')
    try:
        with transaction.atomic():
            return Customer.objects.create(full_name=full_name, phone_number=phone, email=email or None,
                                           line_id=line_id or None, membership_level=level, note=note or '')
    except IntegrityError:
        # Another request created the same phone at the same moment.
        return Customer.objects.get(phone_number=phone)


def _check_email(email):
    if email:
        try:
            validate_email(email)
        except DjangoValidationError:
            raise ServiceError('อีเมลไม่ถูกต้อง')


def _check_password(password, user=None):
    try:
        validate_password(password, user)
    except DjangoValidationError as exc:
        raise ServiceError(' '.join(exc.messages))


@transaction.atomic
def register_member(*, full_name, phone, email, password, username=None):
    """Self sign-up: one login user (role=customer) + one Customer profile."""
    User = get_user_model()
    phone = digits_only(phone)
    full_name = clean_text(full_name, 100)
    email = clean_text(email, 254)
    if not full_name or len(phone) < 9 or not password:
        raise ServiceError('กรุณากรอกข้อมูลที่จำเป็นให้ครบถ้วน (ชื่อ, เบอร์โทร, รหัสผ่าน)')
    _check_email(email)
    username = clean_text(username, 150) or phone
    if not username.replace('_', '').replace('.', '').replace('-', '').isalnum():
        raise ServiceError('ชื่อผู้ใช้งานใช้ได้เฉพาะตัวอักษรภาษาอังกฤษ ตัวเลข และ . _ -')
    if User.objects.filter(username__iexact=username).exists():
        raise ServiceError('ชื่อผู้ใช้นี้ถูกใช้งานในระบบแล้ว')
    if User.objects.filter(phone=phone, role='customer').exists():
        raise ServiceError('เบอร์โทรศัพท์นี้มีบัญชีสมาชิกแล้ว')
    existing = Customer.objects.select_for_update().filter(phone_number=phone).first()
    if existing and existing.user_id:
        raise ServiceError('เบอร์โทรศัพท์นี้มีบัญชีสมาชิกแล้ว')
    user = User(username=username, role='customer', full_name=full_name, phone=phone, email=email)
    _check_password(password, user)
    user.set_password(password)
    user.save()
    if existing:
        # A walk-in customer becomes a member: keep their history and wallet.
        existing.user = user
        existing.email = existing.email or email or None
        existing.save(update_fields=['user', 'email'])
        return user
    Customer.objects.create(user=user, full_name=full_name, phone_number=phone, email=email or None,
                            membership_level=MembershipLevel.objects.filter(level_name__iexact='silver').first())
    return user


@transaction.atomic
def update_member_profile(user, *, full_name=None, email=None, password=None):
    customer = Customer.objects.select_for_update().filter(user=user).first()
    if not customer:
        raise ServiceError('ไม่พบข้อมูลสมาชิก', status=404)
    if full_name:
        user.full_name = customer.full_name = clean_text(full_name, 100)
    if email is not None:
        email = clean_text(email, 254)
        _check_email(email)
        user.email = email
        customer.email = email or None
    if password:
        _check_password(password, user)
        user.set_password(password)
    user.save()
    customer.save(update_fields=['full_name', 'email'])
    return customer
