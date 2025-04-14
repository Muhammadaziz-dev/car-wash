from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'devices', views.DeviceViewSet)
router.register(r'programs', views.WashProgramViewSet)
router.register(r'configurations', views.DeviceConfigurationViewSet)
router.register(r'templates', views.DeviceConfigTemplateViewSet, basename="device-config-template")
router.register(r'logs', views.DeviceLogViewSet)
router.register(r'sessions', views.DeviceSessionViewSet)

urlpatterns = [
    path('', include(router.urls)),
] 