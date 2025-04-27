from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DeviceViewSet,
    WashProgramViewSet,
    DeviceConfigurationViewSet,
    DeviceConfigTemplateViewSet,
    DeviceLogViewSet,
    DeviceSessionViewSet
)

# Primary router for device only
device_router = DefaultRouter()
device_router.register(r'', DeviceViewSet, basename='device')

# Create separate routers for each resource
program_router = DefaultRouter()
program_router.register(r'', WashProgramViewSet, basename='program')

config_router = DefaultRouter()
config_router.register(r'', DeviceConfigurationViewSet, basename='config')

template_router = DefaultRouter()
template_router.register(r'', DeviceConfigTemplateViewSet, basename='template')

log_router = DefaultRouter()
log_router.register(r'', DeviceLogViewSet, basename='log')

session_router = DefaultRouter()
session_router.register(r'', DeviceSessionViewSet, basename='session')

urlpatterns = [
    # Include dedicated paths for each resource
    path('programs/', include(program_router.urls)),
    path('configs/', include(config_router.urls)),
    path('templates/', include(template_router.urls)),
    path('logs/', include(log_router.urls)),
    path('sessions/', include(session_router.urls)),

    # Device-specific actions
    path('<int:pk>/start/', DeviceViewSet.as_view({'post': 'start'}), name='device-start'),
    path('<int:pk>/stop/', DeviceViewSet.as_view({'post': 'stop'}), name='device-stop'),
    path('<int:pk>/pause/', DeviceViewSet.as_view({'post': 'pause'}), name='device-pause'),
    path('<int:pk>/resume/', DeviceViewSet.as_view({'post': 'resume'}), name='device-resume'),
    path('<int:pk>/logs/', DeviceViewSet.as_view({'get': 'logs'}), name='device-logs'),
    path('<int:pk>/sessions/', DeviceViewSet.as_view({'get': 'sessions'}), name='device-sessions'),

    # Config template application endpoint
    path('configs/<int:pk>/apply_template/', DeviceConfigurationViewSet.as_view({'post': 'apply_template'}),
         name='config-apply-template'),
    
    path('configs/<int:pk>/update_performance/', DeviceConfigurationViewSet.as_view({'post': 'update_performance'}), 
     name='config-update-performance'),

    path('<int:pk>/verify/', DeviceViewSet.as_view({'post': 'verify'}), name='device-verify'),
    path('<int:pk>/verify_with_config/', DeviceViewSet.as_view({'post': 'verify_with_config'}), name='device-verify-with-config'),
    path('<int:pk>/update_configuration/', DeviceViewSet.as_view({'post': 'update_configuration'}), name='device-update-configuration'),

    # Include the base device router (must be last to avoid capturing other URLs)
    path('', include(device_router.urls)),
]