from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from .exceptions import ServiceError

CENT = Decimal('0.01')
VAT_RATE = Decimal('7')


def money(value) -> Decimal:
    """Parse any input into a 2-decimal THB amount, or raise a user-facing error."""
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or abs(amount) > Decimal('99999999.99'):
            raise ValueError
        return amount.quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        raise ServiceError('จำนวนเงินไม่ถูกต้อง')


def vat_included(total: Decimal) -> Decimal:
    """VAT portion of a VAT-inclusive total (7/107)."""
    return money(total * VAT_RATE / (Decimal('100') + VAT_RATE))
