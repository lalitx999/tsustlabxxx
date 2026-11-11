"""Customers, payments review, inquiries, reports and settings."""
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.selectors.user_selector import staff_users
from apps.accounts.services import user_service
from apps.catalog.models import CATEGORIES, Brand, PromoCode
from apps.catalog.selectors import catalog_selector
from apps.catalog.services import promo_service, settings_service
from apps.catalog.services.pricing_service import get_policy
from apps.core.decorators import ajax_view, reply, role_required
from apps.core.exceptions import ServiceError
from apps.core.permissions import ADMIN_ROLES, STAFF_ROLES
from apps.customers.selectors import customer_selector
from apps.customers.services import credit_service, topup_service
from apps.inquiries.models import Contact, Partner
from apps.inquiries.services import inquiry_service
from apps.reports.services import report_service

# ---------------------------------------------------------------- customers


@role_required(*STAFF_ROLES)
@require_GET
def customers(request):
    return render(request, 'backoffice/customers.html', {'title': 'Customers'})


@role_required(*STAFF_ROLES)
@require_GET
@ajax_view
def customer_rows(request):
    return [customer_selector.serialize_customer(c) for c in customer_selector.search_customers(request.GET.get('q', ''))]


@role_required(*ADMIN_ROLES)
@require_POST
@ajax_view
def customer_credit(request):
    d = request.json
    entry = credit_service.adjust_credit(customer_id=d.get('customer_id'), amount=d.get('amount'), reason=d.get('reason'),
                                         kind=d.get('type'), request_key=d.get('request_key'), actor=request.user)
    return reply({'credit_balance': str(entry.balance_after)}, message='ปรับยอดเครดิตแล้ว')


# ---------------------------------------------------------------- payments


@role_required(*ADMIN_ROLES)
@require_POST
@ajax_view
def topup_review(request, pk):
    d = request.json
    topup = topup_service.review_topup(pk, action=d.get('action'), reference=d.get('reference'),
                                       amount=d.get('amount'), actor=request.user)
    return reply({'status': topup.status}, message='บันทึกผลแล้ว')


# ---------------------------------------------------------------- inquiries


@role_required(*STAFF_ROLES)
@require_GET
def inquiries(request):
    return render(request, 'backoffice/inquiries.html', {
        'title': 'Partners & Contacts',
        'contacts': Contact.objects.order_by('-created_at')[:200],
        'partners': Partner.objects.order_by('-created_at')[:200],
        'contact_statuses': inquiry_service.CONTACT_STATUSES,
        'partner_statuses': inquiry_service.PARTNER_STATUSES,
    })


MODELS = {'contact': Contact, 'partner': Partner}


@role_required(*STAFF_ROLES)
@require_POST
@ajax_view
def inquiry_update(request, kind, pk):
    model = MODELS.get(kind)
    if model is None:
        raise ServiceError('ไม่พบประเภทข้อมูล', status=404)
    if request.json.get('delete'):
        inquiry_service.delete(model, pk)
        return reply(message='ลบแล้ว')
    inquiry_service.set_status(model, pk, request.json.get('status'))
    return reply(message='อัปเดตสถานะแล้ว')


# ---------------------------------------------------------------- reports


@role_required(*STAFF_ROLES)
@require_GET
def reports(request):
    return render(request, 'backoffice/reports.html', {'title': 'Reports'})


@role_required(*STAFF_ROLES)
@require_GET
@ajax_view
def report_data(request):
    start, end = report_service.parse_period(month=request.GET.get('month'), date_from=request.GET.get('date_from'),
                                             date_to=request.GET.get('date_to'))
    return {'label': report_service.period_label(start, end), 'date_from': start.isoformat(),
            'date_to': end.isoformat(), 'stats': report_service.daily_stats(start, end)}


@role_required(*STAFF_ROLES)
@require_POST
@ajax_view
def report_pdf(request):
    start, end = report_service.parse_period(date_from=request.json.get('date_from'), date_to=request.json.get('date_to'))
    item = report_service.request_report_pdf(start, end, request.user)
    return {'status_url': reverse('core:file_status', args=[item.pk])}


# ---------------------------------------------------------------- users


@role_required(*ADMIN_ROLES)
@require_GET
def users(request):
    return render(request, 'backoffice/users.html', {'title': 'Users', 'users': staff_users()})


@role_required(*ADMIN_ROLES)
@require_POST
@ajax_view
def user_save(request, pk=None):
    user = get_object_or_404(get_user_model(), pk=pk) if pk else None
    if request.json.get('deactivate') and user:
        user_service.delete_staff(user, request.user)
        return reply(message='ปิดการใช้งานบัญชีแล้ว')
    user = user_service.save_staff(request.json, user, actor=request.user)
    return reply({'id': user.pk}, message='บันทึกผู้ใช้แล้ว')


# ---------------------------------------------------------------- pricing


@role_required(*ADMIN_ROLES)
@require_GET
def pricing(request):
    return render(request, 'backoffice/pricing.html', {
        'title': 'Services & Pricing', 'policy': get_policy(), 'packages': catalog_selector.all_packages(),
        'rates': catalog_selector.editable_rates(), 'categories': CATEGORIES,
        'brands': Brand.objects.order_by('brand_name').only('id', 'brand_name'),
    })


@role_required(*ADMIN_ROLES)
@require_POST
@ajax_view
def pricing_save(request):
    d = request.json
    if 'policy' in d:
        settings_service.update_policy(d['policy'])
    if d.get('rate'):
        settings_service.save_rate(d['rate'])
    if d.get('delete_rate_id'):
        settings_service.delete_rate(d['delete_rate_id'])
    if d.get('package'):
        settings_service.set_package_validity(d['package'].get('code'), d['package'].get('validity_days'))
    if d.get('brand_name'):
        settings_service.add_brand(d['brand_name'])
    if d.get('delete_brand_id'):
        settings_service.delete_brand(d['delete_brand_id'])
    return reply(message='บันทึกการตั้งค่าแล้ว')


# ---------------------------------------------------------------- promo codes


@role_required(*ADMIN_ROLES)
@require_GET
def promos(request):
    return render(request, 'backoffice/promos.html', {'title': 'Promo Codes', 'promos': catalog_selector.promo_codes()})


@role_required(*ADMIN_ROLES)
@require_POST
@ajax_view
def promo_save(request, pk=None):
    promo = get_object_or_404(PromoCode, pk=pk) if pk else None
    if request.json.get('delete') and promo:
        result = promo_service.delete_promo(promo)
        return reply(message='ลบโค้ดแล้ว' if result == 'deleted' else 'โค้ดถูกใช้แล้ว จึงปิดการใช้งานแทน')
    promo = promo_service.save_promo(request.json, promo)
    return reply({'id': promo.pk}, message='บันทึกโค้ดส่วนลดแล้ว')
