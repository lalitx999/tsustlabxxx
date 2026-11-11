"""Role checks shared by decorators and services.

Roles come from the legacy system: admin, manager, expert, front, customer.
"""
STAFF_ROLES = ('admin', 'manager', 'front', 'expert')
ADMIN_ROLES = ('admin',)
FRONT_DESK_ROLES = ('admin', 'manager', 'front')
INSPECTOR_ROLES = ('admin', 'expert')
MANAGER_ROLES = ('admin', 'manager')


def has_role(user, roles) -> bool:
    if not (user and user.is_authenticated and user.is_active):
        return False
    return user.is_superuser or getattr(user, 'role', None) in roles


def is_staff_member(user) -> bool:
    return has_role(user, STAFF_ROLES)


def is_admin(user) -> bool:
    return has_role(user, ADMIN_ROLES)


def is_front_desk(user) -> bool:
    return has_role(user, FRONT_DESK_ROLES)


def is_inspector(user) -> bool:
    return has_role(user, INSPECTOR_ROLES)


def is_manager(user) -> bool:
    return has_role(user, MANAGER_ROLES)


def is_customer(user) -> bool:
    return bool(user and user.is_authenticated and user.is_active and getattr(user, 'role', '') == 'customer')
