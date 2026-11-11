"""PromptPay EMVCo QR payload + PNG (ported from the legacy promptpay.py)."""
import base64
from decimal import Decimal
from io import BytesIO

import qrcode
from django.conf import settings

from apps.core.exceptions import ServiceError
from apps.core.money import money


def _crc16(data: str) -> str:
    crc = 0xFFFF
    for char in data.encode('ascii'):
        crc ^= char << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return f'{crc:04X}'


def build_payload(target: str, amount: Decimal | None = None) -> str:
    target = ''.join(ch for ch in target if ch.isdigit())
    if len(target) == 13:
        merchant = f'0016A0000006770101110213{target}'
    elif len(target) in (9, 10):
        phone = f'0066{target.lstrip("0").zfill(9)}'
        merchant = f'0016A0000006770101110113{phone}'
    else:
        raise ServiceError('ยังไม่ได้ตั้งค่าบัญชีรับเงิน PromptPay')
    parts = ['000201', '010211' if amount is None else '010212', f'29{len(merchant):02d}{merchant}', '5303764']
    if amount is not None:
        text = f'{amount:.2f}'
        parts.append(f'54{len(text):02d}{text}')
    parts.append('5802TH')
    partial = ''.join(parts) + '6304'
    return partial + _crc16(partial)


def qr_data_url(amount) -> str:
    """Small CPU-only work (no I/O), fine inside a request."""
    receiver = settings.PROMPTPAY_RECEIVER_ID
    if not receiver or len(receiver) not in (10, 13) or not receiver.isdigit():
        raise ServiceError('ยังไม่ได้ตั้งค่าบัญชีรับเงิน PromptPay')
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=3)
    qr.add_data(build_payload(receiver, money(amount)))
    qr.make(fit=True)
    buffer = BytesIO()
    qr.make_image(fill_color='black', back_color='white').save(buffer, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()


def bank_transfer_details() -> dict:
    return {
        'bank_name': settings.PAYMENT_BANK_NAME or 'ธนาคารกสิกรไทย (KBANK)',
        'account_name': settings.PAYMENT_ACCOUNT_NAME or 'บจก.เซอร์ติฟิเคชั่น แอนด์ อินสเปคชั่น(ไทยแลนด์)',
        'account_number': settings.PAYMENT_ACCOUNT_NUMBER or '238-344-8460',
        'promptpay_no': settings.PROMPTPAY_RECEIVER_ID,
        'enabled': True,
    }


def text_qr_png(text: str) -> bytes:
    """PNG QR for a short text such as a certificate verify link."""
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(text)
    qr.make(fit=True)
    buffer = BytesIO()
    qr.make_image(fill_color='black', back_color='white').save(buffer, format='PNG')
    return buffer.getvalue()
