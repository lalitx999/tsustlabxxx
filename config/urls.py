from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.backoffice.views.pos import pos_display

# Django's built-in admin is kept for superuser maintenance only, on a non-obvious path.
# Staff work in the custom back office at /authenzs/administator/.
admin.site.site_header = 'TRUST LAB — superuser maintenance'

urlpatterns = [
    path('', include('apps.website.urls')),
    path('', include('apps.core.urls')),
    # Same paths as the old site so staff bookmarks keep working.
    path('', include('apps.accounts.urls')),
    path('authenzs/administator/', include('apps.backoffice.urls')),
    path('authenzs/expert/', include('apps.backoffice.expert_urls')),
    path('pos-display/', pos_display, name='pos_display'),
    path('django-admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
