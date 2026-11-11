"""Staff sign-in for the back office. Uses Django sessions (httpOnly cookie), not tokens."""
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from apps.core.permissions import is_staff_member


@require_http_methods(['GET', 'POST'])
def staff_login(request):
    target = request.GET.get('next') or request.POST.get('next') or ''
    if not url_has_allowed_host_and_scheme(target, {request.get_host()}, request.is_secure()):
        target = ''
    if is_staff_member(request.user):
        return redirect(target or 'backoffice:dashboard')
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('username', '').strip(),
                            password=request.POST.get('password', ''))
        if user is None or not is_staff_member(user):
            messages.error(request, 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง')
        else:
            login(request, user)
            return redirect(target or 'backoffice:dashboard')
    return render(request, 'accounts/login.html', {'next': target})


@require_POST
def staff_logout(request):
    logout(request)
    return redirect('accounts:staff_login')
