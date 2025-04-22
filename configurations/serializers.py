# configurations/serializers.py
from rest_framework import serializers
from .models import ConfigurationTemplate, TemplateApplication
from devices.models import Device


class ConfigurationTemplateSerializer(serializers.ModelSerializer):
    created_by = serializers.ReadOnlyField(source='created_by.username')

    class Meta:
        model = ConfigurationTemplate
        fields = ['id', 'name', 'description', 'settings', 'is_active',
                  'created_at', 'updated_at', 'created_by']
        read_only_fields = ['created_at', 'updated_at', 'created_by']

    def validate_settings(self, value):
        """Validate settings format"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Settings must be a JSON object")

        # Check if required settings are present
        required_fields = ['pricing', 'timers']
        missing_fields = [field for field in required_fields if field not in value]
        if missing_fields:
            raise serializers.ValidationError(f"Missing required settings: {', '.join(missing_fields)}")

        return value


class TemplateApplicationSerializer(serializers.ModelSerializer):
    template_name = serializers.ReadOnlyField(source='template.name')
    device_name = serializers.ReadOnlyField(source='device.name')
    applied_by = serializers.ReadOnlyField(source='applied_by.username')

    class Meta:
        model = TemplateApplication
        fields = ['id', 'template', 'template_name', 'device', 'device_name',
                  'applied_at', 'applied_by', 'status', 'error_message']
        read_only_fields = ['applied_at', 'applied_by', 'status', 'error_message']


class ApplyTemplateSerializer(serializers.Serializer):
    """Serializer for applying a template to multiple devices"""
    device_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text="List of device IDs to apply the template to"
    )
    override_existing = serializers.BooleanField(
        default=True,
        help_text="Whether to completely override existing settings or merge them"
    )

    def validate_device_ids(self, value):
        """Validate that all device IDs exist"""
        existing_ids = set(Device.objects.filter(id__in=value).values_list('id', flat=True))
        missing_ids = set(value) - existing_ids

        if missing_ids:
            raise serializers.ValidationError(f"Devices with IDs {missing_ids} do not exist")

        return value