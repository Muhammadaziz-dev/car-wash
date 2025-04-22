# configurations/admin.py
from django.contrib import admin
from .models import ConfigurationTemplate, TemplateApplication


@admin.register(ConfigurationTemplate)
class ConfigurationTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_by', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)
        if obj:  # Editing an existing object
            readonly_fields.append('created_by')
        return readonly_fields

    def save_model(self, request, obj, form, change):
        if not change:  # Creating a new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(TemplateApplication)
class TemplateApplicationAdmin(admin.ModelAdmin):
    list_display = ('template', 'device', 'status', 'applied_by', 'applied_at')
    list_filter = ('status', 'applied_at', 'template')
    search_fields = ('template__name', 'device__name', 'applied_by__username')
    readonly_fields = ('template', 'device', 'applied_by', 'applied_at', 'status', 'error_message')