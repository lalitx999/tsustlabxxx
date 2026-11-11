"""Reference data from the legacy system. get_or_create keeps it safe on an existing database."""
from decimal import Decimal

from django.db import migrations

PACKAGES = [
    ('cert_15d', 'ตรวจสินค้า + แท็ก + ใบรับรอง 15 วัน', 15, 1),
    ('cert_90d', 'ตรวจสินค้า + แท็ก + ใบรับรอง 90 วัน', 90, 2),
    ('photo_review', 'ตรวจผ่านรูปภาพ — 500 บาท ไม่มีใบรับรอง', 0, 3),
]

LEVELS = [
    ('Silver', 'Customer Membership', 'Free Membership', '0.00', '2000.00',
     'รับโปรโมชั่นสะสมแต้มและสิทธิพิเศษสำหรับสมาชิก เช่น ส่วนลดเดือนเกิด, ส่วนลดตามเทศกาล; สิทธิ์เข้าถึงโปรโมชั่นช่วงพิเศษ', '', ''),
    ('Platinum', 'Customer Membership', 'ซื้อเครดิตตรวจ 3,000 THB', '15.00', '1500.00',
     'รับโปรโมชั่นและสิทธิพิเศษสำหรับสมาชิก', 'Priority Service สำหรับสมาชิก', '1 ปี'),
    ('Gold', 'Customer Membership', 'ซื้อเครดิตตรวจ 6,000 THB', '5.00', '1200.00',
     'รับโปรโมชั่นและสิทธิพิเศษสำหรับสมาชิก', 'Priority Queue และ Fast Track Service', '1 ปี'),
    ('Partner', 'Partner Membership', 'ซื้อเครดิตตรวจ 20,000 THB', '0.00', '1000.00',
     'โปรโมชั่นและสิทธิพิเศษสำหรับร้านค้า (ใช้ Partner Rate)', 'สิทธิ์เข้าร่วม Partner Program', '1 ปี'),
]


def seed(apps, schema_editor):
    Package = apps.get_model('catalog', 'ServicePackage')
    Level = apps.get_model('catalog', 'MembershipLevel')
    Policy = apps.get_model('catalog', 'CheckoutPolicy')
    for code, name, days, order in PACKAGES:
        Package.objects.get_or_create(code=code, defaults={'name': name, 'validity_days': days, 'sort_order': order})
    for name, kind, entry, discount, cert, benefits, priority, validity in LEVELS:
        Level.objects.get_or_create(level_name=name, defaults={
            'level_type': kind, 'entry_requirement': entry, 'discount_pct': Decimal(discount),
            'certificate_price': Decimal(cert), 'general_benefits': benefits,
            'priority_service': priority, 'validity_period': validity,
        })
    Policy.objects.get_or_create(pk=1, defaults={
        'approved': True, 'prices_include_vat': True, 'shipping_taxable': False, 'shipping_fee': Decimal('100.00'),
    })


class Migration(migrations.Migration):
    dependencies = [('catalog', '0001_initial')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
