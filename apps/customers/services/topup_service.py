"""Member wallet top-up: PromptPay QR -> slip upload -> admin review."""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.audit.services.audit_service import record_event
from apps.core.exceptions import ServiceError
from apps.core.money import money
from apps.core.services.promptpay import qr_data_url
from apps.core.utils import clean_text, decode_image
from apps.customers.models import Customer, TopupRequest
from apps.customers.services.credit_service import change_credit

MIN_TOPUP = Decimal('100')


def start_topup(user, amount) -> dict:
    customer = Customer.objects.filter(user=user).first()
    if not customer:
        raise ServiceError('ไม่พบข้อมูลสมาชิก', status=404)
    amount = money(amount)
    if amount < MIN_TOPUP:
        raise ServiceError('เติมขั้นต่ำ 100 บาท ผ่าน PromptPay')
    qr = qr_data_url(amount)
    topup = TopupRequest.objects.create(customer=customer, amount=amount)
    return {'topup_id': topup.pk, 'amount': str(amount), 'qr_image': qr}


@transaction.atomic
def submit_slip(user, topup_id, slip_data_url) -> TopupRequest:
    topup = TopupRequest.objects.select_for_update().filter(pk=topup_id, customer__user=user).first()
    if not topup:
        raise ServiceError('ไม่พบรายการเติมเงิน', status=404)
    if topup.status != 'pending':
        raise ServiceError('รายการถูกตรวจสอบแล้ว')
    topup.slip_photo.save(f'topup-{topup.pk}.jpg', decode_image(slip_data_url), save=False)
    topup.save(update_fields=['slip_photo'])
    return topup


@transaction.atomic
def review_topup(topup_id, *, action, reference, amount, actor) -> TopupRequest:
    topup = TopupRequest.objects.select_for_update(of=('self',)).select_related('customer').filter(pk=topup_id).first()
    if not topup:
        raise ServiceError('ไม่พบรายการเติมเงิน', status=404)
    if topup.status != 'pending':
        return topup
    reference = clean_text(reference, 255)
    if action not in ('approve', 'reject') or not reference:
        raise ServiceError('กรุณาระบุผลและเลขอ้างอิง/เหตุผล')
    if action == 'approve':
        if not (topup.slip_photo or topup.evidence) or money(amount) != topup.amount:
            raise ServiceError('กรุณาตรวจหลักฐานและยอดให้ตรง')
        change_credit(topup.customer, topup.amount, f'topup:{topup.pk}', reference, actor)
        topup.approved_at = timezone.now()
    topup.status = 'approved' if action == 'approve' else 'rejected'
    topup.save(update_fields=['status', 'approved_at'])
    record_event(actor, f'topup_{action}', topup_id=topup.pk, reference=reference)
    return topup
