"""View decorators: role checks and the JSON envelope used by every Ajax endpoint."""
import functools
import json
import logging

from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse

from .exceptions import ServiceError
from .permissions import has_role

logger = logging.getLogger(__name__)


def wants_json(request) -> bool:
    return (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or 'application/json' in request.headers.get('Accept', '')
    )


def role_required(*roles, login_url='accounts:staff_login'):
    """Page and Ajax guard.

    Pages: redirect to the login page (via user_passes_test).
    Ajax:  return a JSON 401/403 so the front end can show a message.
    """
    def decorator(view):
        page_guard = user_passes_test(lambda u: has_role(u, roles), login_url=login_url)(view)

        @functools.wraps(view)
        def wrapper(request, *args, **kwargs):
            if wants_json(request):
                if not request.user.is_authenticated:
                    return JsonResponse({'ok': False, 'message': 'กรุณาเข้าสู่ระบบ'}, status=401)
                if not has_role(request.user, roles):
                    return JsonResponse({'ok': False, 'message': 'ไม่มีสิทธิ์ทำรายการนี้'}, status=403)
                return view(request, *args, **kwargs)
            return page_guard(request, *args, **kwargs)
        return wrapper
    return decorator


def ajax_view(view):
    """Wrap an Ajax endpoint: parse JSON body into request.json and map errors.

    The view returns plain data (dict/list) or a JsonResponse/HttpResponse.
    Every JSON reply uses the same envelope: {"ok": bool, "data": ..., "message": str}.
    """
    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        request.json = {}
        if request.content_type == 'application/json' and request.body:
            try:
                request.json = json.loads(request.body)
            except ValueError:
                return JsonResponse({'ok': False, 'message': 'ข้อมูลที่ส่งมาไม่ถูกต้อง'}, status=400)
            if not isinstance(request.json, dict):
                return JsonResponse({'ok': False, 'message': 'ข้อมูลที่ส่งมาไม่ถูกต้อง'}, status=400)
        try:
            result = view(request, *args, **kwargs)
        except ServiceError as exc:
            return JsonResponse({'ok': False, 'message': exc.message, 'code': exc.code}, status=exc.status)
        if hasattr(result, 'status_code'):
            return result
        return reply(result)
    return wrapper


def reply(data=None, message='', status=200):
    """Success envelope for Ajax endpoints."""
    return JsonResponse({'ok': True, 'data': data, 'message': message}, status=status,
                        json_dumps_params={'ensure_ascii': False})
