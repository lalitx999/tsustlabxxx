from django.urls import path

from .views import expert

app_name = 'expert'

urlpatterns = [
    path('jobs/', expert.expert_jobs, name='jobs'),
    path('jobs/rows/', expert.expert_rows, name='rows'),
]
