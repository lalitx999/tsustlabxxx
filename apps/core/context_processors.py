from django.conf import settings

from .permissions import is_customer, is_staff_member


def site(request):
    user = getattr(request, 'user', None)
    return {
        'SITE_NAME': 'TRUST LAB THAILAND',
        'SITE_URL': settings.SITE_URL,
        'lang': getattr(request, 'lang', 'th'),
        'is_staff_member': is_staff_member(user),
        'is_customer': is_customer(user),
    }
