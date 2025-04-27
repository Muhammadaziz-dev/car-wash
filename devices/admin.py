from django.contrib import admin
from .models import (
    Device, WashProgram, DeviceConfiguration, DeviceProgramSetting,
    DeviceLog, DeviceSession
)

class DeviceProgramSettingInline(admin.TabularInline):
    model = DeviceProgramSetting
    extra = 0

class DeviceConfigurationInline(admin.StackedInline):
    model = DeviceConfiguration
    can_delete = False
    show_change_link = True

class DeviceLogInline(admin.TabularInline):
    model = DeviceLog
    extra = 0
    readonly_fields = ['log_type', 'message', 'created_at']
    max_num = 10
    can_delete = False

class DeviceSessionInline(admin.TabularInline):
    model = DeviceSession
    extra = 0
    readonly_fields = ['started_at', 'ended_at', 'status', 'total_duration', 'program', 'amount_charged']
    max_num = 5
    can_delete = False

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ['name', 'device_id', 'status', 'ip_address', 'port', 'is_active', 'last_seen']
    list_filter = ['status', 'is_active', 'created_at']
    search_fields = ['name', 'device_id', 'ip_address', 'location']
    readonly_fields = ['created_at', 'updated_at', 'last_seen']
    inlines = [DeviceConfigurationInline, DeviceLogInline, DeviceSessionInline]

@admin.register(WashProgram)
class WashProgramAdmin(admin.ModelAdmin):
    list_display = ['name', 'price_per_minute', 'price_per_second', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'description']

@admin.register(DeviceConfiguration)
class DeviceConfigurationAdmin(admin.ModelAdmin):
    list_display = ['get_name', 'price_per_minute', 'default_timeout', 'bonus_duration_enabled', 'is_template']
    list_filter = ['bonus_duration_enabled', 'is_template']
    search_fields = ['device__name', 'template_name']
    inlines = [DeviceProgramSettingInline]
    
    def get_name(self, obj):
        if obj.is_template:
            return f"Template: {obj.template_name}"
        return f"Config for {obj.device.name if obj.device else 'Unknown'}"
    get_name.short_description = 'Name'

@admin.register(DeviceLog)
class DeviceLogAdmin(admin.ModelAdmin):
    list_display = ['device', 'log_type', 'message', 'created_at']
    list_filter = ['log_type', 'created_at', 'device']
    search_fields = ['device__name', 'message']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

@admin.register(DeviceSession)
class DeviceSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'device', 'status', 'started_at', 'ended_at', 'total_duration', 'program', 'amount_charged']
    list_filter = ['status', 'started_at', 'device']
    search_fields = ['device__name', 'client_card']
    readonly_fields = ['started_at']
    date_hierarchy = 'started_at'
