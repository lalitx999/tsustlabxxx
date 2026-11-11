from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email

from apps.core.exceptions import ServiceError
from apps.core.utils import clean_text
from apps.inquiries.models import Contact, Partner

CONTACT_STATUSES = ('unread', 'read', 'replied', 'archived')
PARTNER_STATUSES = ('pending', 'approved', 'rejected', 'contacted')


def _email(value):
    value = clean_text(value, 254)
    try:
        validate_email(value)
    except DjangoValidationError:
        raise ServiceError('กรุณาระบุอีเมลให้ถูกต้อง')
    return value


def submit_contact(data: dict) -> Contact:
    name, message = clean_text(data.get('name'), 255), clean_text(data.get('message'), 5000)
    subject = clean_text(data.get('subject'), 200)
    if not name or not message:
        raise ServiceError('กรุณากรอกชื่อและข้อความ')
    if subject:
        message = f'[{subject}] {message}'
    return Contact.objects.create(name=name, email=_email(data.get('email')),
                                  phone=clean_text(data.get('phone'), 50), message=message)


def submit_partner(data: dict) -> Partner:
    business, contact = clean_text(data.get('business_name'), 255), clean_text(data.get('contact_name'), 255)
    phone = clean_text(data.get('phone'), 50)
    if not business or not contact or not phone:
        raise ServiceError('กรุณากรอกชื่อร้าน ชื่อผู้ติดต่อ และเบอร์โทร')
    message = clean_text(data.get('message'), 5000)
    website = clean_text(data.get('website'), 300)
    if website:
        message = f'{message}\nWebsite: {website}'.strip()
    return Partner.objects.create(business_name=business, contact_name=contact, email=_email(data.get('email')),
                                  phone=phone, message=message)


def set_status(model, pk, status) -> None:
    allowed = CONTACT_STATUSES if model is Contact else PARTNER_STATUSES
    if status not in allowed:
        raise ServiceError('สถานะไม่ถูกต้อง')
    if not model.objects.filter(pk=pk).update(status=status):
        raise ServiceError('ไม่พบรายการ', status=404)


def delete(model, pk) -> None:
    model.objects.filter(pk=pk).delete()
