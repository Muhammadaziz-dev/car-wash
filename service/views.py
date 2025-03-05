from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Service, ServiceUsage
from users.models import CustomUser
from .tasks import deduct_balance


class StartServiceView(APIView):
    def post(self, request):
        service_id = request.data.get('service_id')
        user = request.user

        try:
            service = Service.objects.get(id=service_id)
        except Service.DoesNotExist:
            return Response({"error": "Service not found"}, status=status.HTTP_404_NOT_FOUND)

        if user.balance < service.rate_per_second * 5:
            return Response({"error": "Insufficient balance"}, status=status.HTTP_400_BAD_REQUEST)
        usage = ServiceUsage.objects.create(user=user, service=service)
        deduct_balance.apply_async((usage.id,), countdown=5)
        return Response({"message": "Service started", "usage_id": usage.id}, status=status.HTTP_201_CREATED)


class StopServiceView(APIView):
    def post(self, request):
        usage_id = request.data.get('usage_id')
        try:
            usage = ServiceUsage.objects.get(id=usage_id, user=request.user)
        except ServiceUsage.DoesNotExist:
            return Response({"error": "Service usage not found"}, status=status.HTTP_404_NOT_FOUND)

        if usage.is_active:
            usage.is_active = False
            usage.end_time = timezone.now()
            usage.save()
            return Response({"message": "Service stopped"}, status=status.HTTP_200_OK)
        else:
            return Response({"meesage": "Service already stopped"}, status=status.HTTP_200_OK)