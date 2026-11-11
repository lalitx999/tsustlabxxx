from django.http import FileResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET

from .decorators import ajax_view
from .exceptions import ForbiddenError
from .i18n import COOKIE_NAME, LANGUAGES
from .models import GeneratedFile
from .permissions import is_staff_member
from .services.file_service import status_payload


def _can_read(request, item):
    return item.is_public or is_staff_member(request.user) or (
        request.user.is_authenticated and item.requested_by_id == request.user.pk)


@require_GET
@ajax_view
def file_status(request, pk):
    item = get_object_or_404(GeneratedFile, pk=pk)
    if not _can_read(request, item):
        raise ForbiddenError()
    return status_payload(item, reverse('core:file_download', args=[item.pk]))


@require_GET
def file_download(request, pk):
    item = get_object_or_404(GeneratedFile, pk=pk)
    if not _can_read(request, item) or item.status != 'ready' or not item.file:
        raise Http404
    inline = item.content_type == 'application/pdf'
    return FileResponse(item.file.open('rb'), content_type=item.content_type,
                        as_attachment=not inline, filename=item.filename)


@require_GET
def set_language(request, code):
    target = request.GET.get('next', '/')
    if not url_has_allowed_host_and_scheme(target, {request.get_host()}, request.is_secure()):
        target = '/'
    response = HttpResponseRedirect(target)
    if code in LANGUAGES:
        response.set_cookie(COOKIE_NAME, code, max_age=365 * 86400, samesite='Lax')
    return response
