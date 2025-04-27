from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from config.views import debug_urls

schema_view = get_schema_view(
      openapi.Info(
         title="Car Wash Admin API",
         default_version='v1',
         description="API for managing car wash devices, clients, and reporting",
      ),
      public=True,
      permission_classes=[permissions.IsAuthenticated],
   )

urlpatterns = [
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('loyalty/', include('loyalty.urls')),
    path('devices/', include('devices.urls')),
    path('reporting/', include('reporting.urls')),
    path('configurations/', include('configurations.urls')),
    path('debug/', debug_urls),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)