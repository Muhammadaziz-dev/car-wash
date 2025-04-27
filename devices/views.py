from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from decimal import Decimal
from django_filters.rest_framework import DjangoFilterBackend
from devices.services import DeviceBackendService
from devices.configuration import serialize_config

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
    filterset_fields = ['status', 'is_active', 'registration_status']  # Added registration_status
    search_fields = ['name', 'device_id', 'location']
    ordering_fields = ['name', 'created_at', 'status', 'registration_status']  # Added registration_status

    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = [IsOperatorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'is_active', 'registration_status']
    search_fields = ['name', 'device_id', 'location']
    ordering_fields = ['name', 'created_at', 'status', 'registration_status']

    def get_serializer_class(self):
        if self.action in ['retrieve', 'detail']:
            return DeviceDetailSerializer
        return DeviceSerializer

    def _broadcast(self, device):
        broadcast_device_update(device.id, {
            'id': device.id,
            'name': device.name,
            'status': device.status,
            'is_active': device.is_active,
            'registration_status': device.registration_status,
            'last_updated': device.updated_at.isoformat()
        })



    # ... existing actions (verify, start, stop, etc.) remain unchanged ...
    @action(detail=True, methods=['post'], permission_classes=[IsOperator])
    def verify(self, request, pk=None):
        """Manually trigger device verification"""
        device = self.get_object()

        # Get or create device configuration
        config, created = DeviceConfiguration.objects.get_or_create(
            device=device,
            defaults={
                'price_per_minute': Decimal('10.00'),
                'default_timeout': 300,
                'valve_reset_timeout': 60,
                'engine_performance': 50,
                'pump_performance': 50
            }
        )

        # Prepare configuration to send with verification
        config_data = {
            'price_per_minute': float(config.price_per_minute),
            'default_timeout': config.default_timeout,
            'bonus_duration_enabled': config.bonus_duration_enabled,
            'bonus_duration_amount': config.bonus_duration_amount,
            'valve_reset_timeout': config.valve_reset_timeout,
            'engine_performance': config.engine_performance,
            'pump_performance': config.pump_performance,
        }

        # Add program settings if they exist
        program_settings = []
        for ps in config.deviceprogramsetting_set.all():
            program_settings.append({
                'program_id': ps.program.id,
                'program_name': ps.program.name,
                'custom_price': float(ps.custom_price) if ps.custom_price else None,
                'is_enabled': ps.is_enabled
            })
        
        if program_settings:
            config_data['program_settings'] = program_settings

        # Attempt verification with backend
        backend_service = DeviceBackendService()
        success, message = backend_service.verify_device(
            device.device_id,
            device.ip_address,
            device.port,
            configuration=config_data
        )

        device.last_handshake_attempt = timezone.now()

        if success:
            device.registration_status = 'verified'
            device.registration_message = message
            device.save()

            # Log successful verification
            DeviceLog.objects.create(
                device=device,
                log_type='info',
                message=f"Device verified successfully with configuration: {message}"
            )

            # Broadcast the device update
            self._broadcast(device)

            return Response({
                'status': 'verified',
                'message': message
            }, status=status.HTTP_200_OK)
        else:
            device.registration_status = 'pending'  # Keep as pending
            device.registration_message = message
            device.save()

            # Log verification failure
            DeviceLog.objects.create(
                device=device,
                log_type='warning',
                message=f"Device verification failed: {message}"
            )

            # Broadcast the device update
            self._broadcast(device)

            return Response({
                'status': 'pending',
                'message': message
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsOperator])
    def start(self, request, pk=None):
        """Start a new session on this device."""
        device = self.get_object()

        # Check if device is verified before allowing start
        if device.registration_status != 'verified':
            return Response({
                "error": "Cannot start session on unverified device.",
                "registration_status": device.registration_status
            }, status=status.HTTP_400_BAD_REQUEST)

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
    def register(self, request, pk=None):
        device = self.get_object()
        sr = request.data.get("status_report", {})
        ok, payload = DeviceBackendService().register_device(sr)

        device.list_handshake_attempt = timezone.now()
        if not ok:
            device.registration_status = "pending"
            device.registration_message = f"Handshake failed: {payload}"
            device.save()
            self._broadcast(device)
            return Response({"error": payload}, status=202)

        device.device_id = payload["kiosk_id"]

        for comp, detail in payload["status_report"].items():
            level = "info" if detail["status"] == "OK" else "warning"
            DeviceLog.objects.create(
                evice=device,
                log_type=level,
                message=f"{comp}: {detail['status']} — {detail.get('details')}"
            )
        if all(d["status"] == "OK" for d in payload["status_report"].values()):
            device.registration_status = "verified"
            device.registration_message = "All systems OK"
            status_code = 201
        else:
            device.registration_status = "pending"
            device.registration_message = "Some subsystems failed"
            status_code = 202

        device.save()
        self._broadcast(device)
        return Response(self.get_serializer(device).data, status=status_code)

    @action(detail=True, methods=['post'], permission_classes=[IsOperator])
    def stop(self, request, pk=None):
        """Stop the active session and calculate charge."""
        device = self.get_object()

        # Check if device is verified before allowing stop
        if device.registration_status != 'verified':
            return Response({
                "error": "Cannot stop session on unverified device.",
                "registration_status": device.registration_status
            }, status=status.HTTP_400_BAD_REQUEST)

        active_sessions = DeviceSession.objects.filter(device=device, status='active')

        if not active_sessions.exists():
            return Response({"error": "No active session."}, status=status.HTTP_404_NOT_FOUND)

        # If multiple active sessions exist, use the most recent one
        if active_sessions.count() > 1:
            DeviceLog.objects.create(
                device=device,
                log_type='warning',
                message=f"Multiple active sessions found ({active_sessions.count()}). Using most recent."
            )
            session = active_sessions.order_by('-started_at').first()
        else:
            session = active_sessions.first()

        session.status = 'completed'
        session.ended_at = timezone.now()
        duration = (session.ended_at - session.started_at).total_seconds()
        session.total_duration = int(duration)
        if session.program:
            # Calculate using per-second price
            session.amount_charged = session.program.price_per_second * Decimal(str(duration))
        session.save()

        # Cancel any other active sessions if they exist
        active_sessions.exclude(id=session.id).update(status='cancelled', ended_at=timezone.now())

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

        # Check if device is verified before allowing pause
        if device.registration_status != 'verified':
            return Response({
                "error": "Cannot pause session on unverified device.",
                "registration_status": device.registration_status
            }, status=status.HTTP_400_BAD_REQUEST)

        active_sessions = DeviceSession.objects.filter(device=device, status='active')

        if not active_sessions.exists():
            return Response({"error": "No active session."}, status=status.HTTP_404_NOT_FOUND)

        # If multiple active sessions exist, use the most recent one
        if active_sessions.count() > 1:
            DeviceLog.objects.create(
                device=device,
                log_type='warning',
                message=f"Multiple active sessions found ({active_sessions.count()}). Using most recent."
            )
            session = active_sessions.order_by('-started_at').first()
        else:
            session = active_sessions.first()

        session.status = 'paused'
        session.save()

        # Cancel any other active sessions if they exist
        active_sessions.exclude(id=session.id).update(status='cancelled', ended_at=timezone.now())

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

        # Check if device is verified before allowing resume
        if device.registration_status != 'verified':
            return Response({
                "error": "Cannot resume session on unverified device.",
                "registration_status": device.registration_status
            }, status=status.HTTP_400_BAD_REQUEST)

        paused_sessions = DeviceSession.objects.filter(device=device, status='paused')

        if not paused_sessions.exists():
            return Response({"error": "No paused session."}, status=status.HTTP_404_NOT_FOUND)

        # If multiple paused sessions exist, use the most recent one
        if paused_sessions.count() > 1:
            DeviceLog.objects.create(
                device=device,
                log_type='warning',
                message=f"Multiple paused sessions found ({paused_sessions.count()}). Using most recent."
            )
            session = paused_sessions.order_by('-started_at').first()
        else:
            session = paused_sessions.first()

        session.status = 'active'
        session.save()

        # Cancel any other paused sessions if they exist
        paused_sessions.exclude(id=session.id).update(status='cancelled', ended_at=timezone.now())

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

    @action(detail=True, methods=['get'], permission_classes=[IsViewer])
    def status_check(self, request, pk=None):
        """Check device status with the backend"""
        device = self.get_object()

        backend_service = DeviceBackendService()
        online, message = backend_service.check_device_status(device.device_id)

        # Update last seen and status if needed
        if online and device.status != 'online':
            device.status = 'online'
            device.last_seen = timezone.now()
            device.save()
            self._broadcast(device)
        elif not online and device.status == 'online':
            device.status = 'offline'
            device.save()
            self._broadcast(device)

        return Response({
            'status': device.status,
            'online': online,
            'message': message,
            'last_seen': device.last_seen
        })

    @action(detail=True, methods=['post'], permission_classes=[IsOperator])
    def verify_with_config(self, request, pk=None):
        """Verify device and send its configuration"""
        device = self.get_object()
        
        # Get device configuration if it exists
        try:
            config = device.configuration
            # Create configuration data dictionary to send
            config_data = {
                'price_per_minute': float(config.price_per_minute),
                'default_timeout': config.default_timeout,
                'bonus_duration_enabled': config.bonus_duration_enabled,
                'bonus_duration_amount': config.bonus_duration_amount,
                'valve_reset_timeout': config.valve_reset_timeout,
                'engine_performance': config.engine_performance,
                'pump_performance': config.pump_performance,
            }
            
            # Add program settings if they exist
            program_settings = []
            for ps in config.deviceprogramsetting_set.all():
                program_settings.append({
                    'program_id': ps.program.id,
                    'program_name': ps.program.name,
                    'custom_price': float(ps.custom_price) if ps.custom_price else None,
                    'is_enabled': ps.is_enabled
                })
            
            if program_settings:
                config_data['program_settings'] = program_settings
                
        except Exception as e:
            # If no configuration exists, create default
            config = DeviceConfiguration.objects.create(
                device=device,
                price_per_minute=Decimal('10.00'),
                default_timeout=300,
                valve_reset_timeout=60,
                engine_performance=50,
                pump_performance=50
            )
            config_data = {
                'price_per_minute': float(config.price_per_minute),
                'default_timeout': config.default_timeout,
                'bonus_duration_enabled': config.bonus_duration_enabled,
                'bonus_duration_amount': config.bonus_duration_amount,
                'valve_reset_timeout': config.valve_reset_timeout,
                'engine_performance': config.engine_performance,
                'pump_performance': config.pump_performance,
            }
        
        # Attempt verification with backend including configuration
        backend_service = DeviceBackendService()
        success, message = backend_service.verify_device(
            device.device_id,
            device.ip_address,
            device.port,
            configuration=config_data
        )
        
        device.last_handshake_attempt = timezone.now()
        
        if success:
            device.registration_status = 'verified'
            device.registration_message = message
            device.save()
            
            # Log successful verification
            DeviceLog.objects.create(
                device=device,
                log_type='info',
                message=f"Device verified successfully with configuration: {message}"
            )
            
            # Broadcast the device update
            self._broadcast(device)
            
            return Response({
                'status': 'verified',
                'message': message
            }, status=status.HTTP_200_OK)
        else:
            device.registration_status = 'pending'  # Keep as pending
            device.registration_message = message
            device.save()
            
            # Log verification failure
            DeviceLog.objects.create(
                device=device,
                log_type='warning',
                message=f"Device verification with configuration failed: {message}"
            )
            
            # Broadcast the device update
            self._broadcast(device)
            
            return Response({
                'status': 'pending',
                'message': message
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsOperator])
    def update_configuration(self, request, pk=None):
        device = self.get_object()
        if device.registration_status != "verified":
            return Response({"error": "Unverified"}, status=400)

        config = device.configuration
        payload = serialize_config(config, include_programs=True)

        ok, msg = DeviceBackendService().send_device_configuration(payload)
        DeviceLog.objects.create(
            device=device,
            log_type="info" if ok else "warning",
            message=f"Config update {'succeeded' if ok else 'failed'}: {msg}"
        )
        return Response({"status": "success" if ok else "error", "message": msg},
                        status=200 if ok else 400)


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
    def update_performance(self, request, pk=None):
        """Update device performance settings."""
        device_config = self.get_object()

        # Get performance values from request
        engine_performance = request.data.get('engine_performance')
        pump_performance = request.data.get('pump_performance')

        # Update if provided
        if engine_performance is not None:
            device_config.engine_performance = engine_performance
        if pump_performance is not None:
            device_config.pump_performance = pump_performance

        device_config.save()

        # Broadcast update if device has a device attribute
        if hasattr(device_config, 'device'):
            broadcast_device_update(device_config.device.id, {
                'id': device_config.device.id,
                'name': device_config.device.name,
                'status': device_config.device.status,
                'is_active': device_config.device.is_active,
                'performance': {
                    'engine': device_config.engine_performance,
                    'pump': device_config.pump_performance,
                },
                'last_updated': device_config.device.updated_at.isoformat()
            })

        return Response(DeviceConfigurationSerializer(device_config).data)

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
