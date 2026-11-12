from django.urls import path

from .views import admin_pages as admin, bookings, dashboard, documents, jobs, pages

app_name = 'backoffice'

urlpatterns = [
    path('', dashboard.dashboard, name='home'),
    path('dashboard/', dashboard.dashboard, name='dashboard'),

    # Walk-in & bookings
    path('walk-in/', bookings.walkin, name='walkin'),
    path('walk-in/customer/', bookings.customer_lookup, name='walkin_customer'),
    path('walk-in/quote/', bookings.walkin_quote, name='walkin_quote'),
    path('walk-in/create/', bookings.walkin_create, name='walkin_create'),
    path('walk-in/<int:pk>/update/', bookings.walkin_update, name='walkin_update'),
    path('booking/', bookings.bookings, name='bookings'),
    path('bookings/rows/', bookings.booking_rows, name='booking_rows'),
    path('bookings/<str:pk>/', bookings.booking_get, name='booking_get'),
    path('bookings/<str:pk>/check-in/', bookings.booking_check_in, name='booking_check_in'),
    path('bookings/<str:pk>/payment/', bookings.booking_counter_payment, name='booking_payment'),
    path('bookings/<str:pk>/qr/', bookings.booking_qr, name='booking_qr'),
    path('bookings/<str:pk>/slip-review/', bookings.booking_slip_review, name='booking_slip_review'),
    path('bookings/<str:pk>/cancel/', bookings.booking_cancel, name='booking_cancel'),
    path('bookings/<str:pk>/photos/', jobs.booking_photos_add, name='booking_photos_add'),
    path('bookings/<str:pk>/photos/<int:photo_id>/delete/', jobs.booking_photo_delete, name='booking_photo_delete'),
    path('bookings/<str:pk>/documents/', documents.document_issue, name='document_issue'),
    path('bookings/<int:pk>/intake-slip/', documents.intake_print, name='intake_print'),
    path('documents/<int:pk>/print/', documents.document_print, name='document_print'),
    path('documents/<int:pk>/void/', documents.document_void, name='document_void'),
    path('cancellations/<int:pk>/review/', bookings.cancellation_review, name='cancellation_review'),

    # Jobs & inspection
    path('jobs/', jobs.jobs, name='jobs'),
    path('jobs/rows/', jobs.job_rows, name='job_rows'),
    path('jobs/<str:pk>/', jobs.job_get, name='job_get'),
    path('jobs/<str:pk>/result/', jobs.job_result, name='job_result'),
    path('jobs/<str:pk>/details/', jobs.job_details, name='job_details'),
    path('jobs/<str:pk>/shipping/', jobs.job_shipping, name='job_shipping'),
    path('jobs/<str:pk>/label/', jobs.job_label, name='job_label'),
    path('jobs/<str:pk>/photos-zip/', jobs.job_photo_zip, name='job_photo_zip'),

    # Certificates
    path('auth/certificates/', jobs.certificates, name='certificates'),
    path('certificates/rows/', jobs.certificate_rows, name='certificate_rows'),
    path('certificates/issue/', jobs.certificate_issue, name='certificate_issue'),
    path('certificates/<str:pk>/code/', jobs.certificate_code, name='certificate_code'),
    path('certificates/<str:pk>/revoke/', jobs.certificate_revoke, name='certificate_revoke'),
    path('certificates/<str:pk>/expire/', jobs.certificate_expire, name='certificate_expire'),
    path('certificates/<str:pk>/send/', jobs.certificate_send, name='certificate_send'),
    path('certificates/<str:pk>/photos/', jobs.certificate_photos, name='certificate_photos'),
    path('certificates/<str:pk>/pdf/', jobs.certificate_pdf, name='certificate_pdf'),

    # Customers, payments, inquiries
    path('customers/', admin.customers, name='customers'),
    path('customers/rows/', admin.customer_rows, name='customer_rows'),
    path('customers/credit/', admin.customer_credit, name='customer_credit'),
    path('topups/<int:pk>/review/', admin.topup_review, name='topup_review'),
    path('contacts/', admin.inquiries, name='inquiries'),
    path('inquiries/<str:kind>/<int:pk>/', admin.inquiry_update, name='inquiry_update'),

    # Read-only pages (same menu as the old admin)
    path('queue/', pages.queue, name='queue'),
    path('operations/', pages.operations, name='operations'),
    path('auth/progress/', pages.progress, name='progress'),
    path('auth/completed/', pages.completed, name='completed'),
    path('auth/qr/', pages.qr, name='qr'),
    path('membership/', pages.membership, name='membership'),
    path('analytics/', pages.analytics, name='analytics'),
    path('settings/system/', pages.system, name='system'),

    # Reports
    path('reports/', admin.reports, name='reports'),
    path('reports/data/', admin.report_data, name='report_data'),
    path('reports/pdf/', admin.report_pdf, name='report_pdf'),

    # Settings
    path('settings/users/', admin.users, name='users'),
    path('settings/users/save/', admin.user_save, name='user_create'),
    path('settings/users/<int:pk>/save/', admin.user_save, name='user_save'),
    path('settings/pricing/', admin.pricing, name='pricing'),
    path('settings/pricing/save/', admin.pricing_save, name='pricing_save'),
    path('settings/promo-codes/', admin.promos, name='promos'),
    path('settings/promo-codes/save/', admin.promo_save, name='promo_create'),
    path('settings/promo-codes/<int:pk>/save/', admin.promo_save, name='promo_save'),
]
