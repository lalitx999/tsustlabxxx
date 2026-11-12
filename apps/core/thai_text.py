"""Spell out a THB amount in Thai words, as printed on receipts and tax invoices."""
from decimal import Decimal

from .money import money

DIGITS = ('ศูนย์', 'หนึ่ง', 'สอง', 'สาม', 'สี่', 'ห้า', 'หก', 'เจ็ด', 'แปด', 'เก้า')
UNITS = ('', 'สิบ', 'ร้อย', 'พัน', 'หมื่น', 'แสน')


def _below_million(n: int, *, has_higher: bool) -> str:
    """Words for 0..999,999. `has_higher` means digits exist to the left (so a trailing 1 is 'เอ็ด')."""
    text = []
    digits = str(n)
    length = len(digits)
    for i, ch in enumerate(digits):
        d = int(ch)
        pos = length - i - 1
        if d == 0:
            continue
        if pos == 0 and d == 1 and (length > 1 or has_higher):
            text.append('เอ็ด')
        elif pos == 1 and d == 1:
            text.append('สิบ')
        elif pos == 1 and d == 2:
            text.append('ยี่สิบ')
        else:
            text.append(DIGITS[d] + UNITS[pos])
    return ''.join(text)


def number_text(n: int) -> str:
    if n == 0:
        return DIGITS[0]
    groups = []
    while n > 0:
        groups.append(n % 1_000_000)
        n //= 1_000_000
    text = ''
    for i in range(len(groups) - 1, -1, -1):
        part = _below_million(groups[i], has_higher=i < len(groups) - 1)
        text += part
        if i > 0 and (part or text):
            text += 'ล้าน'
    return text


def baht_text(amount) -> str:
    """1250.50 -> 'หนึ่งพันสองร้อยห้าสิบบาทห้าสิบสตางค์', 100 -> 'หนึ่งร้อยบาทถ้วน'."""
    value = money(amount)
    sign = 'ลบ' if value < 0 else ''
    value = abs(value)
    baht = int(value)
    satang = int((value - Decimal(baht)) * 100)
    words = sign + number_text(baht) + 'บาท'
    return words + (number_text(satang) + 'สตางค์' if satang else 'ถ้วน')
