from django.db.models import Min, Q

from apps.customers.models import CreditEntry, Customer, TopupRequest


def _with_first_service(queryset):
    return queryset.select_related('membership_level').annotate(
        first_service_at=Min('job__created_at', filter=~Q(job__status='cancelled')))


def search_customers(query: str = '', *, limit=50):
    queryset = Customer.objects.all()
    query = (query or '').strip()
    if query:
        queryset = queryset.filter(Q(full_name__icontains=query) | Q(phone_number__contains=query))
    return _with_first_service(queryset).order_by('-created_at')[:limit]


def customer_by_phone(phone: str):
    return Customer.objects.select_related('membership_level').filter(phone_number=phone).first()


def customer_for_user(user):
    if not (user and user.is_authenticated):
        return None
    return Customer.objects.select_related('membership_level').filter(user=user).first()


def members(*, limit=500):
    return _with_first_service(Customer.objects.exclude(membership_level=None)).order_by('-credit_balance')[:limit]


def recent_credit_entries(*, limit=200):
    return CreditEntry.objects.select_related('customer', 'actor').order_by('-created_at')[:limit]


def pending_topups():
    return TopupRequest.objects.select_related('customer').filter(status='pending').order_by('created_at')


def serialize_customer(customer) -> dict:
    return {
        'id': customer.pk,
        'full_name': customer.full_name,
        'phone_number': customer.phone_number,
        'email': customer.email or '',
        'line_id': customer.line_id or '',
        'membership_level': customer.tier_name,
        'credit_balance': str(customer.credit_balance),
        'account_type': customer.account_type,
        'first_service_at': getattr(customer, 'first_service_at', None),
    }
