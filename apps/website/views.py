"""Public website pages and their Ajax endpoints.

Views only: read the request -> call a service/selector -> render or return JSON.
"""
import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.bookings.selectors.booking_selector import bookings_for_customer
from apps.bookings.services.booking_service import create_booking, read_receipt, resolve_customer
from apps.catalog.services.pricing_service import load_signed_quote, quote, sign_quote
from apps.core.decorators import ajax_view, reply, role_required
from apps.core.exceptions import ForbiddenError, ServiceError
from apps.core.permissions import is_customer, is_front_desk, is_staff_member
from apps.core.services.promptpay import bank_transfer_details, qr_data_url
from apps.customers.selectors.customer_selector import customer_for_user
from apps.customers.services import customer_service, topup_service
from apps.inquiries.services import inquiry_service
from apps.inspections.selectors.job_selector import find_certificate, serialize_certificate_public
from apps.inspections.services.certificate_service import request_pdf

from .content import (ABOUT_VALUES, BOOKING_SLOTS, BOOKING_STEPS, CATEGORY_BRANDS, THAI_PROVINCES, CHECKPOINT_BOXES, CONTACT_INFO, HERO_IMAGES, HOME,
                      HOME_BRANDS, LAB_TOOLS, NAV, PARTNER_BENEFITS, SERVICE_CATEGORIES, SERVICE_PACKAGES, STEP_ICONS,
                      TRUSTEE_PARTNERS, copy_for)



def _page(request, template, context=None, pages=(), active=None):
    lang = request.lang
    data = {
        'copy': copy_for(lang, *pages),
        'nav': [(key, url_name, key == active) for key, url_name in NAV],
        'nav_active': active,
    }
    data.update(context or {})
    return render(request, template, data)


# ---------------------------------------------------------------- static pages

@require_GET
def home(request):
    copy = copy_for(request.lang, HOME)
    return _page(request, 'website/home.html', {
        'slides': list(zip(HERO_IMAGES, copy['slides'])), 'brands': HOME_BRANDS, 'partners': TRUSTEE_PARTNERS,
        'step_icons': STEP_ICONS, 'review_video_url': settings.REVIEW_VIDEO_URL,
    }, (HOME,), 'home')


@require_GET
def about(request):
    return _page(request, 'website/about.html', {'values': ABOUT_VALUES}, active='about')


@require_GET
def services(request):
    return _page(request, 'website/services.html', {
        'packages': SERVICE_PACKAGES, 'categories': SERVICE_CATEGORIES,
    }, active='services')


@require_GET
def process(request):
    return _page(request, 'website/process.html', {
        'step_icons': STEP_ICONS, 'boxes': CHECKPOINT_BOXES, 'tools': LAB_TOOLS,
    }, (HOME,), 'authProcess')


@require_GET
def terms(request):
    from apps.inspections.service_terms import IMPORTANT_NOTICE, IMPORTANT_NOTICE_TH
    return render(request, 'website/terms.html', {'notice': IMPORTANT_NOTICE, 'notice_th': IMPORTANT_NOTICE_TH})


@require_GET
def privacy(request):
    return render(request, 'website/privacy.html', {'today': timezone.localdate()})


# ---------------------------------------------------------------- verify

@require_GET
def verify(request):
    return _page(request, 'website/verify.html', {'initial_id': request.GET.get('id', '')[:60]}, active='certVerify')


@require_GET
@ajax_view
def verify_lookup(request):
    cert = find_certificate(request.GET.get('id', '')[:60])
    if not cert or cert.job.service_package == 'photo_review':
        raise ServiceError('ไม่พบหมายเลขใบรับรองในระบบ', status=404)
    data = serialize_certificate_public(cert)
    data['pdf_url'] = reverse('website:certificate_pdf', args=[cert.cert_code])
    return data


@require_POST
@ajax_view
def certificate_pdf(request, code):
    """Queue the PDF (Celery) and return a status URL for polling."""
    cert = find_certificate(code)
    if not cert:
        raise ServiceError('ไม่พบใบรับรอง', status=404)
    item = request_pdf(cert, request.user)
    return {'status_url': reverse('core:file_status', args=[item.pk])}


@role_required('admin', 'manager', 'front', 'expert')
@require_GET
def qr_image(request):
    """QR sticker image for a certificate verify link (staff only)."""
    from django.http import HttpResponse, HttpResponseBadRequest
    from apps.core.services.promptpay import text_qr_png

    text = request.GET.get('text', '')
    if not text or len(text) > 300:
        return HttpResponseBadRequest('invalid text')
    response = HttpResponse(text_qr_png(text), content_type='image/png')
    response['Cache-Control'] = 'private, max-age=3600'
    return response


# ---------------------------------------------------------------- contact / partner

@require_GET
def contact(request):
    return _page(request, 'website/contact.html', {'info': CONTACT_INFO}, active='contact')


@require_POST
@ajax_view
def contact_submit(request):
    inquiry_service.submit_contact(request.json)
    return reply(message='ส่งข้อความเรียบร้อยแล้ว ทีมงานจะติดต่อกลับโดยเร็ว', status=201)


@require_GET
def partner(request):
    return _page(request, 'website/partner.html', {'benefits': PARTNER_BENEFITS}, active='partner')


@require_POST
@ajax_view
def partner_submit(request):
    inquiry_service.submit_partner(request.json)
    return reply(message='ส่งใบสมัครเรียบร้อยแล้ว ทีมงานจะติดต่อกลับภายใน 1-2 วันทำการ', status=201)


# ---------------------------------------------------------------- booking

@require_GET
def booking(request):
    from apps.accounts.models import Branch
    return _page(request, 'website/booking.html', {
        'branches': Branch.objects.filter(is_active=True).only('id', 'name', 'address').order_by('id'),
        'step_titles': BOOKING_STEPS, 'time_slots': BOOKING_SLOTS, 'provinces': THAI_PROVINCES,
        'category_brands': CATEGORY_BRANDS,
        'today': timezone.localdate().isoformat(),
        'max_date': (timezone.localdate() + datetime.timedelta(days=60)).isoformat(),
        'customer': customer_for_user(request.user),
        'bank': bank_transfer_details(),
    })


@require_POST
@ajax_view
def booking_quote(request):
    customer = resolve_customer(request.user, request.json)
    snapshot = quote(request.json, customer, allow_manual_price=is_front_desk(request.user))
    return {**snapshot, 'quote_token': sign_quote(snapshot, customer)}


@require_POST
@ajax_view
def booking_promptpay(request):
    snapshot = load_signed_quote(request.json.get('quote_token'))
    return {'qr_image': qr_data_url(snapshot['total']), 'amount': snapshot['total'], **bank_transfer_details()}


@require_GET
@ajax_view
def booking_slots(request):
    return [{'slot': slot, 'available': True} for slot in BOOKING_SLOTS]


@require_POST
@ajax_view
def booking_create(request):
    result = create_booking(request.user, request.json)
    booking = result['booking']
    return reply({
        'booking_id': booking.display_id,
        'payment_status': booking.payment_status,
        'receipt_url': reverse('website:booking_result') + '?token=' + result['receipt_token'],
    }, message='จองคิวเรียบร้อยแล้ว', status=201 if result['created'] else 200)


@require_GET
def booking_result(request):
    try:
        receipt = read_receipt(request.GET.get('token'))
    except ServiceError as exc:
        receipt, error = None, exc.message
    else:
        error = ''
    return _page(request, 'website/booking_result.html', {'receipt': receipt, 'error': error})


# ---------------------------------------------------------------- member portal

def _member_username(value: str) -> str:
    """Members may sign in with their username or their phone number (like the old site)."""
    from django.contrib.auth import get_user_model
    value = value.strip()
    digits = ''.join(c for c in value if c.isdigit())
    if digits and digits == value:
        user = get_user_model().objects.filter(phone=digits, role='customer').only('username').first()
        if user:
            return user.username
    return value


@require_http_methods(['GET', 'POST'])
def member_login(request):
    if is_customer(request.user):
        return redirect('website:member_dashboard')
    if request.method == 'POST':
        user = authenticate(request, username=_member_username(request.POST.get('username', '')),
                            password=request.POST.get('password', ''))
        if user is None or not user.is_active:
            messages.error(request, 'ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง')
        elif is_staff_member(user):
            messages.error(request, 'บัญชีพนักงานกรุณาเข้าสู่ระบบที่หน้าระบบหลังบ้าน')
        else:
            login(request, user)
            return redirect('website:member_dashboard')
    return _page(request, 'website/member_login.html', {'username': request.POST.get('username', ''), 'hide_flash': True}, active='login')


@require_http_methods(['GET', 'POST'])
def member_register(request):
    if request.method == 'POST':
        try:
            user = customer_service.register_member(
                username=request.POST.get('username'), full_name=request.POST.get('full_name'),
                phone=request.POST.get('phone'), email=request.POST.get('email'), password=request.POST.get('password'))
        except ServiceError as exc:
            messages.error(request, exc.message)
        else:
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'สมัครสมาชิกเรียบร้อยแล้ว')
            return redirect('website:member_dashboard')
    return _page(request, 'website/member_register.html', {'form': request.POST, 'hide_flash': True}, active='login')


@require_POST
def member_logout(request):
    logout(request)
    return redirect('website:home')


@role_required('customer', login_url='website:member_login')
@require_GET
def member_dashboard(request):
    customer = customer_for_user(request.user)
    return _page(request, 'website/member_dashboard.html', {
        'customer': customer, 'member_tab': 'overview',
        'bookings': bookings_for_customer(customer) if customer else [],
    }, active='member')


@role_required('customer', login_url='website:member_login')
@require_http_methods(['GET', 'POST'])
def member_profile(request):
    if request.method == 'GET':
        return _page(request, 'website/member_profile.html', {
            'customer': customer_for_user(request.user), 'member_tab': 'profile'}, active='member')
    return _member_profile_save(request)


@ajax_view
def _member_profile_save(request):
    data = request.json
    if data.get('password') and data.get('password') != data.get('confirm_password'):
        raise ServiceError('รหัสผ่านใหม่และการยืนยันไม่ตรงกัน')
    customer_service.update_member_profile(request.user, full_name=data.get('full_name'),
                                           email=data.get('email'), password=data.get('password') or None)
    return reply(message='อัปเดตข้อมูลโปรไฟล์ส่วนตัวสำเร็จ')


@role_required('customer', login_url='website:member_login')
@require_POST
@ajax_view
def member_topup(request):
    return reply(topup_service.start_topup(request.user, request.json.get('amount')), status=201)


@role_required('customer', login_url='website:member_login')
@require_POST
@ajax_view
def member_topup_slip(request):
    topup_service.submit_slip(request.user, request.json.get('topup_id'), request.json.get('slip'))
    return reply(message='รับสลิปแล้ว รอผู้ดูแลตรวจสอบก่อนเพิ่มเครดิต')


@role_required('customer', login_url='website:member_login')
@require_POST
@ajax_view
def member_cancel(request, booking_id):
    """A member may cancel only their own booking."""
    from apps.bookings.models import Booking
    from apps.bookings.services.cancellation_service import request_cancel

    if not Booking.objects.filter(pk=booking_id, customer__user=request.user).exists():
        raise ForbiddenError()
    return reply(request_cancel(booking_id, reason=request.json.get('reason'), actor=request.user))
