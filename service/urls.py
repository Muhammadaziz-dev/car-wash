from django.urls import path
from .views import StartServiceView, StopServiceView


urlpatterns = [
    path('start/', StartServiceView.as_view(), name='start-service'),
    path('stop/', StopServiceView.as_view(), name='stop-service'),
]