from django.contrib.auth import get_user_model

from apps.core.permissions import STAFF_ROLES


def staff_users():
    return (get_user_model().objects.filter(role__in=STAFF_ROLES).select_related('branch')
            .only('id', 'username', 'full_name', 'email', 'phone', 'role', 'is_active', 'last_login', 'branch__name')
            .order_by('role', 'username'))


def experts():
    return list(get_user_model().objects.filter(role__in=('expert', 'admin'), is_active=True)
                .order_by('full_name').values('id', 'full_name', 'username'))
