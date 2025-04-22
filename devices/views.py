from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from accounts.permissions import (
    IsOperatorOrReadOnly,
    IsOperator,
    IsViewer,
)
from .models import (
    Device, WashProgram, DeviceConfiguration, DeviceProgramSetting,
    DeviceLog, DeviceSession
)
from .serializers import (
    DeviceSerializer, WashProgramSerializer, DeviceConfigurationSerializer,
    DeviceProgramSettingSerializer, DeviceLogSerializer, DeviceSessionSerializer,
    DeviceDetailSerializer, DeviceConfigTemplateSerializer
)
from .utils import broadcast_device_update


class DeviceViewSet(viewsets.ModelViewSet):
    """
    CRUD + command actions for devices, with real-time broadcasts.
    """
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = [IsOperatorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'is_active']
    search_fields = ['name', 'device_id', 'location']
    ordering_fields = ['name', 'created_at', 'status']

    def get_serializer_class(self):
        if self.action in ['retrieve', 'detail']:
            return DeviceDetailSerializer
        return DeviceSerializer

    def _broadcast(self, device):
        """Helper to send updated device state over WebSocket."""
        broadcast_device_update(device.id, {
            'id': device.id,
            'name': device.name,
            'status': device.status,
            'is_active': device.is_active,
            'last_updated': device.updated_at.isoformat()
        })

    @action(detail=True, methods=['post'], permission_classes=[IsOperator])
    def start(self, request, pk=None):
        """Start a new session on this device."""
        device = self.get_object()
        program_id = request.data.get('program_id')
        client_card = request.data.get('client_card')
        if not program_id:
            return Response({"error": "Program ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        program = get_object_or_404(WashProgram, pk=program_id)

        if DeviceSession.objects.filter(device=device, status='active').exists():
            return Response({"error": "Active session exists."}, status=status.HTTP_400_BAD_REQUEST)

        session = DeviceSession.objects.create(
            device=device,
            program=program,
            client_card=client_card,
            status='active'
        )
        DeviceLog.objects.create(
            device=device,
            log_type='command',
            message=f"Started session: {program.name}"
        )

        # Update and broadcast device status
        device.status = 'online'
        device.last_seen = timezone.now()
        device.save()
        self._broadcast(device)

        return Response(DeviceSessionSerializer(session).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[IsOperator])
    def stop(self, request, pk=None):
        """Stop the active session and calculate charge."""
        device = self.get_object()
        try:
            session = DeviceSession.objects.get(device=device, status='active')
        except DeviceSession.DoesNotExist:
            return Response({"error": "No active session."}, status=status.HTTP_404_NOT_FOUND)

        session.status = 'completed'
        session.ended_at = timezone.now()
        duration = (session.ended_at - session.started_at).total_seconds()
        session.total_duration = int(duration)
        if session.program:
            minutes = duration / 60
            session.amount_charged = session.program.price_per_minute * minutes
        session.save()

        DeviceLog.objects.create(
            device=device,
            log_type='command',
            message=f"Stopped session: {session.total_duration}s"
        )

        # Update and broadcast device status
        device.status = 'offline'
        device.save()
        self._broadcast(device)

        return Response(DeviceSessionSerializer(session).data)

    @action(detail=True, methods=['post'], permission_classes=[IsOperator])
    def pause(self, request, pk=None):
        """Pause the active session."""
        device = self.get_object()
        try:
            session = DeviceSession.objects.get(device=device, status='active')
        except DeviceSession.DoesNotExist:
            return Response({"error": "No active session."}, status=status.HTTP_404_NOT_FOUND)

        session.status = 'paused'
        session.save()
        DeviceLog.objects.create(device=device, log_type='command', message="Paused session")

        # Broadcast pause (device remains online)
        device.status = 'online'
        device.save()
        self._broadcast(device)

        return Response(DeviceSessionSerializer(session).data)

    @action(detail=True, methods=['post'], permission_classes=[IsOperator])
    def resume(self, request, pk=None):
        """Resume a paused session."""
        device = self.get_object()
        try:
            session = DeviceSession.objects.get(device=device, status='paused')
        except DeviceSession.DoesNotExist:
            return Response({"error": "No paused session."}, status=status.HTTP_404_NOT_FOUND)

        session.status = 'active'
        session.save()
        DeviceLog.objects.create(device=device, log_type='command', message="Resumed session")

        # Broadcast resume
        device.status = 'online'
        device.save()
        self._broadcast(device)

        return Response(DeviceSessionSerializer(session).data)

    @action(detail=True, methods=['get'], permission_classes=[IsViewer])
    def logs(self, request, pk=None):
        """List device logs, with optional filtering."""
        device = self.get_object()
        logs = device.logs.all()
        log_type = request.query_params.get('type')
        if log_type:
            logs = logs.filter(log_type=log_type)
        page = self.paginate_queryset(logs)
        if page is not None:
            serializer = DeviceLogSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = DeviceLogSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], permission_classes=[IsViewer])
    def sessions(self, request, pk=None):
        """List all sessions for this device."""
        device = self.get_object()
        sessions = device.sessions.all()
        status_filter = request.query_params.get('status')
        if status_filter:
            sessions = sessions.filter(status=status_filter)
        page = self.paginate_queryset(sessions)
        if page is not None:
            serializer = DeviceSessionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = DeviceSessionSerializer(sessions, many=True)
        return Response(serializer.data)


class WashProgramViewSet(viewsets.ModelViewSet):
    queryset = WashProgram.objects.all()
    serializer_class = WashProgramSerializer
    permission_classes = [IsOperatorOrReadOnly]


class DeviceConfigurationViewSet(viewsets.ModelViewSet):
    queryset = DeviceConfiguration.objects.filter(is_template=False)
    serializer_class = DeviceConfigurationSerializer
    permission_classes = [IsOperatorOrReadOnly]

    @action(detail=False, methods=['get'], permission_classes=[IsViewer])
    def templates(self, request):
        """List all configuration templates."""
        templates = DeviceConfiguration.objects.filter(is_template=True)
        serializer = DeviceConfigTemplateSerializer(templates, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsOperator])
    def apply_template(self, request, pk=None):
        """Apply a template to this device configuration."""
        device_config = self.get_object()
        template_id = request.data.get('template_id')
        if not template_id:
            return Response({"error": "Template ID required."}, status=status.HTTP_400_BAD_REQUEST)
        template = get_object_or_404(DeviceConfiguration, pk=template_id, is_template=True)

        # Copy fields
        device_config.price_per_minute = template.price_per_minute
        device_config.default_timeout = template.default_timeout
        device_config.bonus_duration_enabled = template.bonus_duration_enabled
        device_config.bonus_duration_amount = template.bonus_duration_amount
        device_config.valve_reset_timeout = template.valve_reset_timeout
        device_config.save()

        # Copy program settings
        device_config.deviceprogramsetting_set.all().delete()
        for ts in template.deviceprogramsetting_set.all():
            DeviceProgramSetting.objects.create(
                device_config=device_config,
                program=ts.program,
                custom_price=ts.custom_price,
                is_enabled=ts.is_enabled
            )

        # Broadcast the updated device configuration
        broadcast_device_update(device_config.device.id, {
            'id': device_config.device.id,
            'name': device_config.device.name,
            'status': device_config.device.status,
            'is_active': device_config.device.is_active,
            'last_updated': device_config.device.updated_at.isoformat()
        })

        return Response(DeviceConfigurationSerializer(device_config).data)


class DeviceConfigTemplateViewSet(viewsets.ModelViewSet):
    queryset = DeviceConfiguration.objects.filter(is_template=True)
    serializer_class = DeviceConfigTemplateSerializer
    permission_classes = [IsOperatorOrReadOnly]


class DeviceLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DeviceLog.objects.all()
    serializer_class = DeviceLogSerializer
    permission_classes = [IsViewer]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['device', 'log_type']
    ordering = ['-created_at']


class DeviceSessionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DeviceSession.objects.all()
    serializer_class = DeviceSessionSerializer
    permission_classes = [IsViewer]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['device', 'status', 'program']
    ordering = ['-started_at']
