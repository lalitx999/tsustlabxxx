"""TrustLab Cam (/trustlabcam/): phone camera for staff to add inspection photos to a booking."""
import datetime

from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.bookings.selectors import booking_selector
from apps.core.decorators import ajax_view, role_required
from apps.core.exceptions import ServiceError
from apps.core.permissions import STAFF_ROLES, is_staff_member
from apps.inspections.services.photo_service import MAX_STAFF_PHOTOS


@require_GET
def cam_home(request):
    """Signed-in staff go straight to the day list; others see the Cam sign-in screen."""
    if is_staff_member(request.user):
        return redirect('camera:jobs')
    return render(request, 'camera/login.html', {'next': '/trustlabcam/jobs/'})


@role_required(*STAFF_ROLES)
@require_GET
def cam_jobs(request):
    return render(request, 'camera/jobs.html', {'today': timezone.localdate().isoformat(), 'max_photos': MAX_STAFF_PHOTOS})


@role_required(*STAFF_ROLES)
@require_GET
@ajax_view
def cam_rows(request):
    raw = request.GET.get('date') or ''
    try:
        day = datetime.date.fromisoformat(raw) if raw else timezone.localdate()
    except ValueError:
        raise ServiceError('วันที่ไม่ถูกต้อง')
    return [booking_selector.serialize_camera_booking(b) for b in booking_selector.camera_bookings(day)]


@role_required(*STAFF_ROLES)
@require_GET
def cam_capture(request, pk):
    booking = booking_selector.camera_bookings_one(pk)
    if not booking:
        raise Http404
    return render(request, 'camera/capture.html', {
        'booking': booking_selector.serialize_camera_booking(booking), 'max_photos': MAX_STAFF_PHOTOS,
    })
