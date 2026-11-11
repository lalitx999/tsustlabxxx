"""Back-office sidebar — same sections, labels and icons as the old admin layout.

Each item lists the roles that may see it.
"""
from apps.core.permissions import ADMIN_ROLES, FRONT_DESK_ROLES, STAFF_ROLES

MENU = [
    ('MAIN MENU', [
        ('Dashboard', 'backoffice:dashboard', 'layout-dashboard', STAFF_ROLES),
        ('Walk-in (New Sale)', 'backoffice:walkin', 'user-plus', FRONT_DESK_ROLES),
        ('Booking', 'backoffice:bookings', 'calendar', FRONT_DESK_ROLES),
        ('Job List', 'backoffice:jobs', 'list-todo', STAFF_ROLES),
        ('Queue Management', 'backoffice:queue', 'hourglass', STAFF_ROLES),
        ('Operations & Delivery', 'backoffice:operations', 'truck', FRONT_DESK_ROLES),
    ]),
    ('AUTHENTICATION', [
        ('In Progress', 'backoffice:progress', 'activity', STAFF_ROLES),
        ('Completed', 'backoffice:completed', 'circle-check', STAFF_ROLES),
        ('Certificate', 'backoffice:certificates', 'award', STAFF_ROLES),
        ('QR Verification', 'backoffice:qr', 'qr-code', STAFF_ROLES),
    ]),
    ('CUSTOMER', [
        ('Customers', 'backoffice:customers', 'users', STAFF_ROLES),
        ('Membership', 'backoffice:membership', 'credit-card', STAFF_ROLES),
        ('Partners & Contacts', 'backoffice:inquiries', 'mail', STAFF_ROLES),
    ]),
    ('REPORT', [
        ('Reports', 'backoffice:reports', 'file-text', STAFF_ROLES),
        ('Analytics', 'backoffice:analytics', 'chart-column', STAFF_ROLES),
    ]),
    ('SETTING', [
        ('Users', 'backoffice:users', 'user-check', ADMIN_ROLES),
        ('Services & Pricing', 'backoffice:pricing', 'badge-dollar-sign', ADMIN_ROLES),
        ('Promo Codes', 'backoffice:promos', 'tag', ADMIN_ROLES),
        ('System Settings', 'backoffice:system', 'settings', ADMIN_ROLES),
    ]),
]


def menu_for(user, current_url_name):
    role = 'admin' if user.is_superuser else getattr(user, 'role', '')
    sections = []
    for title, items in MENU:
        visible = [
            {'label': label, 'url_name': url_name, 'icon': icon, 'active': url_name == current_url_name}
            for label, url_name, icon, roles in items if role in roles
        ]
        if visible:
            sections.append({'title': title, 'items': visible})
    return sections
