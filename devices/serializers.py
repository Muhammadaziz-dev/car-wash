from rest_framework import serializers
from .models import Device, WashProgram, DeviceConfiguration, DeviceProgramSetting, DeviceLog, DeviceSession

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ['id', 'name', 'device_id', 'status', 'ip_address', 'port', 
                 'location', 'created_at', 'updated_at', 'is_active', 'last_seen']
        read_only_fields = ['created_at', 'updated_at', 'last_seen']

class WashProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = WashProgram
        fields = ['id', 'name', 'description', 'price_per_minute', 'is_active']

class DeviceProgramSettingSerializer(serializers.ModelSerializer):
    program_name = serializers.CharField(source='program.name', read_only=True)
    
    class Meta:
        model = DeviceProgramSetting
        fields = ['id', 'program', 'program_name', 'custom_price', 'is_enabled']

class DeviceConfigurationSerializer(serializers.ModelSerializer):
    program_settings = DeviceProgramSettingSerializer(source='deviceprogramsetting_set', many=True, read_only=True)
    
    class Meta:
        model = DeviceConfiguration
        fields = ['id', 'device', 'price_per_minute', 'default_timeout', 
                 'bonus_duration_enabled', 'bonus_duration_amount', 
                 'valve_reset_timeout', 'is_template', 'template_name',
                 'program_settings', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class DeviceConfigTemplateSerializer(serializers.ModelSerializer):
    program_settings = DeviceProgramSettingSerializer(source='deviceprogramsetting_set', many=True, read_only=True)
    
    class Meta:
        model = DeviceConfiguration
        fields = ['id', 'price_per_minute', 'default_timeout', 
                 'bonus_duration_enabled', 'bonus_duration_amount', 
                 'valve_reset_timeout', 'template_name',
                 'program_settings', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['is_template'] = True
        return super().create(validated_data)

class DeviceLogSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.name', read_only=True)
    
    class Meta:
        model = DeviceLog
        fields = ['id', 'device', 'device_name', 'log_type', 'message', 'created_at']
        read_only_fields = ['created_at']

class DeviceSessionSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.name', read_only=True)
    program_name = serializers.CharField(source='program.name', read_only=True)
    duration_minutes = serializers.SerializerMethodField()
    
    class Meta:
        model = DeviceSession
        fields = ['id', 'device', 'device_name', 'started_at', 'ended_at', 
                 'status', 'total_duration', 'duration_minutes', 'program', 
                 'program_name', 'client_card', 'amount_charged', 'bonus_time_used']
        read_only_fields = ['created_at', 'duration_minutes']
    
    def get_duration_minutes(self, obj):
        return round(obj.total_duration / 60, 2) if obj.total_duration else 0

class DeviceDetailSerializer(serializers.ModelSerializer):
    configuration = DeviceConfigurationSerializer(read_only=True)
    active_session = serializers.SerializerMethodField()
    
    class Meta:
        model = Device
        fields = ['id', 'name', 'device_id', 'status', 'ip_address', 'port', 
                 'location', 'created_at', 'updated_at', 'is_active', 
                 'last_seen', 'configuration', 'active_session']
        read_only_fields = ['created_at', 'updated_at', 'last_seen']
    
    def get_active_session(self, obj):
        active_sessions = obj.sessions.filter(status='active').first()
        if active_sessions:
            return DeviceSessionSerializer(active_sessions).data
        return None 