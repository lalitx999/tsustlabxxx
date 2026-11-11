"""Wallet ledger. Every change locks the customer row and writes a CreditEntry."""
import uuid
from decimal import Decimal

from django.db import transaction

from apps.core.exceptions import ServiceError
from apps.core.money import money
from apps.customers.models import CreditEntry, Customer


@transaction.atomic
def change_credit(customer: Customer, amount: Decimal, reference: str, reason: str, actor) -> CreditEntry:
    """Idempotent by `reference`: retrying the same request does not double-charge."""
    locked = Customer.objects.select_for_update().get(pk=customer.pk)
    existing = CreditEntry.objects.filter(reference=reference).first()
    if existing:
        if existing.customer_id != locked.pk or existing.amount != amount:
            raise ServiceError('รหัสรายการซ้ำกับธุรกรรมอื่น')
        return existing
    balance = money(locked.credit_balance + amount)
    if balance < 0:
        raise ServiceError('ยอดเครดิตสะสมไม่เพียงพอ')
    locked.credit_balance = balance
    locked.save(update_fields=['credit_balance'])
    customer.credit_balance = balance
    return CreditEntry.objects.create(customer=locked, amount=amount, balance_after=balance,
                                      reference=reference, reason=reason, actor=actor)


def adjust_credit(*, customer_id, amount, reason, kind, request_key, actor) -> CreditEntry:
    """Admin manual top-up/deduction."""
    customer = Customer.objects.filter(pk=customer_id).first()
    if not customer:
        raise ServiceError('ไม่พบลูกค้า', status=404)
    amount = money(amount)
    reason = str(reason or '').strip()
    try:
        key = uuid.UUID(str(request_key))
    except ValueError:
        raise ServiceError('กรุณาระบุรหัสรายการ')
    if amount <= 0 or not reason or kind not in ('add', 'deduct'):
        raise ServiceError('ระบุจำนวนเงินบวก เหตุผล และประเภทปรับยอด')
    signed = amount if kind == 'add' else -amount
    return change_credit(customer, signed, f'adjust:{key}', reason, actor)
