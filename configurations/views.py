# configurations/views.py
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import ConfigurationTemplate, TemplateApplication
from .serializers import (
    ConfigurationTemplateSerializer,
    TemplateApplicationSerializer,
    ApplyTemplateSerializer
)
from devices.models import Device
from accounts.permissions import IsOperator, IsAdmin, IsViewer


class ConfigurationTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing device configuration templates
    """
    queryset = ConfigurationTemplate.objects.all()
    serializer_class = ConfigurationTemplateSerializer

    def get_permissions(self):
        """
        - List/Retrieve: Any authenticated user
        - Create/Update: Only operators and admins
        - Delete: Only admins
        """
        if self.action == 'destroy':
            permission_classes = [IsAdmin]
        elif self.action in ['create', 'update', 'partial_update', 'apply']:
            permission_classes = [IsOperator]
        else:
            permission_classes = [IsViewer]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def apply(self, request, pk=None):
        """
        Apply this configuration template to multiple devices

        Expected payload:
        {
            "device_ids": [1, 2, 3, ...],
            "override_existing": true/false (optional)
        }
        """
        template = self.get_object()
        serializer = ApplyTemplateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        device_ids = serializer.validated_data['device_ids']
        override_existing = serializer.validated_data['override_existing']

        # Get all specified devices
        devices = Device.objects.filter(id__in=device_ids)

        # Apply template to each device
        applied_devices = []
        errors = []

        for device in devices:
            try:
                # Get current settings or initialize empty dict
                current_settings = device.settings if hasattr(device, 'settings') else {}

                if isinstance(current_settings, dict) and override_existing:
                    # Complete override with template settings
                    device.settings = template.settings.copy()
                elif isinstance(current_settings, dict):
                    # Merge settings, keeping existing values for keys not in template
                    merged_settings = current_settings.copy()
                    merged_settings.update(template.settings)
                    device.settings = merged_settings
                else:
                    # Initialize settings if they don't exist or are invalid
                    device.settings = template.settings.copy()

                # Save the device with new settings
                device.save()

                # Create application record
                application = TemplateApplication.objects.create(
                    template=template,
                    device=device,
                    applied_by=request.user,
                    status='success'
                )

                applied_devices.append({
                    "id": device.id,
                    "name": device.name,
                    "application_id": application.id,
                    "status": "success"
                })

            except Exception as e:
                # Record failed application
                try:
                    application = TemplateApplication.objects.create(
                        template=template,
                        device=device,
                        applied_by=request.user,
                        status='failed',
                        error_message=str(e)
                    )
                except:
                    pass  # If we can't record the failure, continue

                errors.append({
                    "id": device.id,
                    "name": getattr(device, 'name', f"Device {device.id}"),
                    "status": "error",
                    "message": str(e)
                })

        # Return results
        return Response({
            "template": {
                "id": template.id,
                "name": template.name
            },
            "results": {
                "success_count": len(applied_devices),
                "error_count": len(errors),
                "applied_devices": applied_devices,
                "errors": errors
            }
        })


class TemplateApplicationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing template application history (read-only)
    """
    queryset = TemplateApplication.objects.all()
    serializer_class = TemplateApplicationSerializer
    permission_classes = [IsViewer]

    def get_queryset(self):
        queryset = TemplateApplication.objects.all()

        # Filter by template
        template_id = self.request.query_params.get('template_id')
        if template_id:
            queryset = queryset.filter(template_id=template_id)

        # Filter by device
        device_id = self.request.query_params.get('device_id')
        if device_id:
            queryset = queryset.filter(device_id=device_id)

        # Filter by status
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(applied_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(applied_at__lte=end_date)

        return queryset