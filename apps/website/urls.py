from django.urls import path

from . import views

app_name = 'website'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('authentication-process/', views.process, name='process'),
    path('terms/', views.terms, name='terms'),
    path('privacy-policy/', views.privacy, name='privacy'),

    path('verify/', views.verify, name='verify'),
    path('verify/lookup/', views.verify_lookup, name='verify_lookup'),
    path('certificates/<str:code>/pdf/', views.certificate_pdf, name='certificate_pdf'),
    path('qr.png', views.qr_image, name='qr_image'),

    path('contact/', views.contact, name='contact'),
    path('contact/submit/', views.contact_submit, name='contact_submit'),
    path('partner/', views.partner, name='partner'),
    path('partner/submit/', views.partner_submit, name='partner_submit'),

    path('booking/', views.booking, name='booking'),
    path('booking/quote/', views.booking_quote, name='booking_quote'),
    path('booking/promptpay/', views.booking_promptpay, name='booking_promptpay'),
    path('booking/slots/', views.booking_slots, name='booking_slots'),
    path('booking/create/', views.booking_create, name='booking_create'),
    path('booking/result/', views.booking_result, name='booking_result'),

    path('member/login/', views.member_login, name='member_login'),
    path('member/register/', views.member_register, name='member_register'),
    path('member/logout/', views.member_logout, name='member_logout'),
    path('member/', views.member_dashboard, name='member_dashboard'),
    path('member/profile/', views.member_profile, name='member_profile'),
    path('member/topup/', views.member_topup, name='member_topup'),
    path('member/topup/slip/', views.member_topup_slip, name='member_topup_slip'),
    path('member/bookings/<int:booking_id>/cancel/', views.member_cancel, name='member_cancel'),
]
