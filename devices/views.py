from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import (
    Device, WashProgram, DeviceConfiguration, DeviceProgramSetting,
    DeviceLog, DeviceSession
)
from .serializers import (
    DeviceSerializer, WashProgramSerializer, DeviceConfigurationSerializer,
    DeviceProgramSettingSerializer, DeviceLogSerializer, DeviceSessionSerializer,
    DeviceDetailSerializer, DeviceConfigTemplateSerializer
)

class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'is_active']
    search_fields = ['name', 'device_id', 'location']
    ordering_fields = ['name', 'created_at', 'status']

    def get_serializer_class(self):
        if self.action == 'retrieve' or self.action == 'detail':
            return DeviceDetailSerializer
        return DeviceSerializer

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        device = self.get_object()
        program_id = request.data.get('program_id')
        client_card = request.data.get('client_card')
        
        if not program_id:
            return Response({"error": "Program ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        program = get_object_or_404(WashProgram, pk=program_id)
        
        # Check if there's an active session already
        if DeviceSession.objects.filter(device=device, status='active').exists():
            return Response({"error": "Device already has an active session"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create new session
        session = DeviceSession.objects.create(
            device=device,
            program=program,
            client_card=client_card,
            status='active'
        )
        
        # Log the action
        DeviceLog.objects.create(
            device=device,
            log_type='command',
            message=f"Started session with program: {program.name}"
        )
        
        # Update device status
        device.status = 'online'
        device.last_seen = timezone.now()
        device.save()
        
        return Response(DeviceSessionSerializer(session).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        device = self.get_object()
        
        # Find active session
        try:
            session = DeviceSession.objects.get(device=device, status='active')
        except DeviceSession.DoesNotExist:
            return Response({"error": "No active session found"}, status=status.HTTP_404_NOT_FOUND)
        
        # End the session
        session.status = 'completed'
        session.ended_at = timezone.now()
        duration = (session.ended_at - session.started_at).total_seconds()
        session.total_duration = int(duration)
        
        # Calculate charge based on duration and program price
        if session.program:
            minutes = duration / 60
            session.amount_charged = session.program.price_per_minute * minutes
        
        session.save()
        
        # Log the action
        DeviceLog.objects.create(
            device=device,
            log_type='command',
            message=f"Stopped session. Duration: {session.total_duration} seconds"
        )
        
        return Response(DeviceSessionSerializer(session).data)

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        device = self.get_object()
        
        # Find active session
        try:
            session = DeviceSession.objects.get(device=device, status='active')
        except DeviceSession.DoesNotExist:
            return Response({"error": "No active session found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Pause the session
        session.status = 'paused'
        session.save()
        
        # Log the action
        DeviceLog.objects.create(
            device=device,
            log_type='command',
            message="Paused session"
        )
        
        return Response(DeviceSessionSerializer(session).data)

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        device = self.get_object()
        
        # Find paused session
        try:
            session = DeviceSession.objects.get(device=device, status='paused')
        except DeviceSession.DoesNotExist:
            return Response({"error": "No paused session found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Resume the session
        session.status = 'active'
        session.save()
        
        # Log the action
        DeviceLog.objects.create(
            device=device,
            log_type='command',
            message="Resumed session"
        )
        
        return Response(DeviceSessionSerializer(session).data)

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        device = self.get_object()
        logs = device.logs.all()
        
        # Apply filters if provided
        log_type = request.query_params.get('type')
        if log_type:
            logs = logs.filter(log_type=log_type)
        
        # Apply pagination
        page = self.paginate_queryset(logs)
        if page is not None:
            serializer = DeviceLogSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = DeviceLogSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def sessions(self, request, pk=None):
        device = self.get_object()
        sessions = device.sessions.all()
        
        # Apply filters if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            sessions = sessions.filter(status=status_filter)
        
        # Apply pagination
        page = self.paginate_queryset(sessions)
        if page is not None:
            serializer = DeviceSessionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = DeviceSessionSerializer(sessions, many=True)
        return Response(serializer.data)

class WashProgramViewSet(viewsets.ModelViewSet):
    queryset = WashProgram.objects.all()
    serializer_class = WashProgramSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']

class DeviceConfigurationViewSet(viewsets.ModelViewSet):
    queryset = DeviceConfiguration.objects.filter(is_template=False)
    serializer_class = DeviceConfigurationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def templates(self, request):
        templates = DeviceConfiguration.objects.filter(is_template=True)
        serializer = DeviceConfigTemplateSerializer(templates, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def apply_template(self, request, pk=None):
        device_config = self.get_object()
        template_id = request.data.get('template_id')
        
        if not template_id:
            return Response({"error": "Template ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            template = DeviceConfiguration.objects.get(pk=template_id, is_template=True)
        except DeviceConfiguration.DoesNotExist:
            return Response({"error": "Template not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Copy template settings to device configuration
        device_config.price_per_minute = template.price_per_minute
        device_config.default_timeout = template.default_timeout
        device_config.bonus_duration_enabled = template.bonus_duration_enabled
        device_config.bonus_duration_amount = template.bonus_duration_amount
        device_config.valve_reset_timeout = template.valve_reset_timeout
        device_config.save()
        
        # Clear existing program settings
        device_config.deviceprogramsetting_set.all().delete()
        
        # Copy program settings from template
        for template_setting in template.deviceprogramsetting_set.all():
            DeviceProgramSetting.objects.create(
                device_config=device_config,
                program=template_setting.program,
                custom_price=template_setting.custom_price,
                is_enabled=template_setting.is_enabled
            )
        
        return Response(DeviceConfigurationSerializer(device_config).data)

class DeviceConfigTemplateViewSet(viewsets.ModelViewSet):
    queryset = DeviceConfiguration.objects.filter(is_template=True)
    serializer_class = DeviceConfigTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

class DeviceLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DeviceLog.objects.all()
    serializer_class = DeviceLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['device', 'log_type']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

class DeviceSessionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DeviceSession.objects.all()
    serializer_class = DeviceSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['device', 'status', 'program']
    ordering_fields = ['started_at', 'ended_at']
    ordering = ['-started_at']
