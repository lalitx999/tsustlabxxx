"""Job list, expert inspection, shipping, photos and certificates."""
from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.selectors.user_selector import experts
from apps.bookings.selectors.booking_selector import photo_urls
from apps.core.decorators import ajax_view, reply, role_required
from apps.core.exceptions import ServiceError
from apps.core.permissions import ADMIN_ROLES, FRONT_DESK_ROLES, INSPECTOR_ROLES, STAFF_ROLES, has_role
from apps.core.utils import parse_pk
from apps.inspections.selectors import job_selector
from apps.inspections.services import certificate_service, job_service, photo_service, shipping_service

INSPECTION_ROLES = INSPECTOR_ROLES + ('manager',)


@role_required(*STAFF_ROLES)
@require_GET
def jobs(request):
    return render(request, 'backoffice/jobs.html', {'title': 'Job List', 'experts': experts()})


@role_required(*STAFF_ROLES)
@require_GET
@ajax_view
def job_rows(request):
    status = request.GET.get('status')
    rows = job_selector.job_list(status=status.split(',') if status else None, query=request.GET.get('q') or None)
    return [job_selector.serialize_job(j) for j in rows]


@role_required(*STAFF_ROLES)
@require_GET
@ajax_view
def job_get(request, pk):
    job = job_selector.job_detail(parse_pk(pk))
    if not job:
        raise ServiceError('ไม่พบงาน', status=404)
    data = job_selector.serialize_job(job)
    data['photos'] = photo_urls(job.booking) if job.booking_id else {'customer': [], 'staff': []}
    return data


@role_required(*INSPECTION_ROLES)
@require_POST
@ajax_view
def job_result(request, pk):
    job = job_service.record_result(pk, request.json, request.user)
    return reply(job_selector.serialize_job(job_selector.job_detail(job.pk)), message='บันทึกผลตรวจแล้ว')


@role_required(*FRONT_DESK_ROLES)
@require_POST
@ajax_view
def job_details(request, pk):
    """Front desk edits item details (serial, colour, accessories...)."""
    job = job_selector.job_detail(parse_pk(pk))
    if not job or not job.booking_id:
        raise ServiceError('ไม่พบงาน', status=404)
    job_service.check_in(job.booking_id, request.json, request.user)
    return reply(message='บันทึกข้อมูลสินค้าแล้ว')


@role_required(*FRONT_DESK_ROLES)
@require_POST
@ajax_view
def job_shipping(request, pk):
    status = shipping_service.update_shipping(pk, new_status=request.json.get('shipping_status'),
                                              tracking_number=request.json.get('tracking_number'), actor=request.user)
    return reply({'status': status}, message='อัปเดตสถานะส่งคืนแล้ว')


@role_required(*FRONT_DESK_ROLES)
@require_POST
@ajax_view
def job_label(request, pk):
    item = shipping_service.request_return_label(pk, request.user)
    return {'status_url': reverse('core:file_status', args=[item.pk])}


@role_required(*STAFF_ROLES)
@require_POST
@ajax_view
def job_photo_zip(request, pk):
    item = photo_service.request_photo_zip(pk, request.user)
    return {'status_url': reverse('core:file_status', args=[item.pk])}


@role_required(*STAFF_ROLES)
@require_POST
@ajax_view
def booking_photos_add(request, pk):
    photos = photo_service.add_staff_photos(pk, request.json.get('photos'), request.user)
    return reply(photos, message=f'อัปโหลด {len(photos)} รูปแล้ว', status=201)


@role_required(*STAFF_ROLES)
@require_POST
@ajax_view
def booking_photo_delete(request, pk, photo_id):
    photo_service.delete_photo(pk, photo_id, request.user)
    return reply(message='ลบรูปภาพเรียบร้อย')


# ---------------------------------------------------------------- certificates

@role_required(*STAFF_ROLES)
@require_GET
def certificates(request):
    return render(request, 'backoffice/certificates.html', {'title': 'Certificate'})


PACKAGE_NAMES = {'cert_15d': 'ตรวจสอบสินค้า + ใบรับรอง 15 วัน', 'cert_90d': 'ตรวจสอบสินค้า + ใบรับรอง 90 วัน',
                 'photo_review': 'Photo Review'}


def _timeline(cert, job, booking):
    paid = job.payment_status == 'paid' or (booking and booking.payment_status == 'paid')
    started = job.status in ('in_progress', 'completed')
    done = job.status == 'completed'
    created = booking.created_at if booking else job.created_at
    return [
        {'label': 'สร้างงาน', 'date': created, 'done': True},
        {'label': 'รอการชำระเงิน', 'date': created, 'done': True},
        {'label': 'ชำระเงินแล้ว', 'date': job.updated_at if paid else None, 'done': paid},
        {'label': 'กำลังตรวจสอบ', 'date': job.updated_at if started else None, 'done': started},
        {'label': 'ตรวจสอบเสร็จสิ้น', 'date': job.updated_at if done else None, 'done': done},
        {'label': 'ใบรับรองถูกระงับ' if cert.cert_status == 'revoked' else 'ออกใบเซอร์แล้ว',
         'date': cert.created_at, 'done': True, 'final': True},
    ]


@role_required(*STAFF_ROLES)
@require_GET
def certificate_detail(request, code):
    cert = job_selector.certificate_detail(code)
    if not cert:
        raise Http404
    job, booking = cert.job, cert.job.booking
    snapshot = (booking.price_snapshot if booking else None) or job.price_snapshot or {}
    verify_url = f"{settings.SITE_URL}{reverse('website:verify')}?id={cert.cert_code or cert.pk}"
    return render(request, 'backoffice/certificate_detail.html', {
        'title': 'Certificate Detail', 'cert': cert, 'job': job, 'booking': booking, 'customer': job.customer,
        'photos': job_selector.certificate_photos(cert), 'send_logs': cert.send_logs.all(),
        'expert': job.result_recorded_by.display_name if job.result_recorded_by else (job.expert_source or '-'),
        'price': snapshot, 'package_name': PACKAGE_NAMES.get(job.service_package, job.service_package),
        'timeline': _timeline(cert, job, booking), 'verify_url': verify_url,
        'can_select_photos': has_role(request.user, INSPECTION_ROLES),
        'max_photos': certificate_service.MAX_CERT_PHOTOS,
    })


@role_required(*STAFF_ROLES)
@require_GET
@ajax_view
def certificate_rows(request):
    rows = job_selector.certificate_list(query=request.GET.get('q') or None, status=request.GET.get('status') or None)
    return [{
        'id': c.pk, 'code': c.cert_code, 'status': c.cert_status, 'brand': c.job.brand, 'model': c.job.model,
        'customer': c.job.customer.full_name, 'email': c.job.customer.email or '',
        'issued': c.created_at.isoformat(), 'expires': c.expires_at.isoformat() if c.expires_at else '',
        'job_id': c.job_id, 'job_display_id': c.job.display_id, 'serial': c.job.serial_number or '',
    } for c in rows]


def _certificate(pk):
    cert = job_selector.find_certificate(pk)
    if not cert:
        raise ServiceError('ไม่พบใบรับรอง', status=404)
    return cert


@role_required(*INSPECTION_ROLES)
@require_POST
@ajax_view
def certificate_issue(request):
    cert = certificate_service.issue_for_job(parse_pk(request.json.get('job_id')), request.json.get('cert_code'),
                                             request.user)
    return reply({'code': cert.cert_code}, message='ออกใบรับรองแล้ว', status=201)


@role_required(*STAFF_ROLES)
@require_POST
@ajax_view
def certificate_code(request, pk):
    cert = certificate_service.change_code(_certificate(pk), request.json.get('cert_code'))
    return reply({'code': cert.cert_code}, message='เปลี่ยนเลขใบเซอร์แล้ว')


@role_required(*ADMIN_ROLES)
@require_POST
@ajax_view
def certificate_revoke(request, pk):
    certificate_service.revoke(_certificate(pk), request.json.get('reason'), request.user)
    return reply(message='เพิกถอนใบรับรองแล้ว')


@role_required(*ADMIN_ROLES)
@require_POST
@ajax_view
def certificate_expire(request, pk):
    certificate_service.expire(_certificate(pk), request.user)
    return reply(message='ตั้งสถานะหมดอายุแล้ว')


@role_required(*STAFF_ROLES)
@require_POST
@ajax_view
def certificate_send(request, pk):
    certificate_service.send(_certificate(pk), request.json.get('method'), request.json.get('recipient'))
    return reply(message='ส่งเข้าคิวการจัดส่งแล้ว')


@role_required(*INSPECTION_ROLES)
@require_POST
@ajax_view
def certificate_photos(request, pk):
    certificate_service.select_photos(_certificate(pk), request.json.get('photo_ids') or [], request.user)
    return reply(message='บันทึกรูปบนใบรับรองแล้ว')


@role_required(*STAFF_ROLES)
@require_POST
@ajax_view
def certificate_pdf(request, pk):
    item = certificate_service.request_pdf(_certificate(pk), request.user)
    return {'status_url': reverse('core:file_status', args=[item.pk])}
