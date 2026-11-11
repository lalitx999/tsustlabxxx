from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('files/<int:pk>/status/', views.file_status, name='file_status'),
    path('files/<int:pk>/download/', views.file_download, name='file_download'),
    path('lang/<str:code>/', views.set_language, name='set_language'),
]
