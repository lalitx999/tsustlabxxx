from django.urls import path

from .views import camera

app_name = 'camera'

urlpatterns = [
    path('', camera.cam_home, name='home'),
    path('jobs/', camera.cam_jobs, name='jobs'),
    path('jobs/rows/', camera.cam_rows, name='rows'),
    path('jobs/<int:pk>/', camera.cam_capture, name='capture'),
]
