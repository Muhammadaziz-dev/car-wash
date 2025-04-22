# configurations/models.py
from django.db import models
from django.core.exceptions import ValidationError
import json


class ConfigurationTemplate(models.Model):
    """
    Model to store device configuration templates that can be applied to multiple devices
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    settings = models.JSONField(help_text="Device configuration settings")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True,
                                   related_name='templates')

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Configuration Template"
        verbose_name_plural = "Configuration Templates"

    def __str__(self):
        return self.name

    def clean(self):
        """Validate settings format"""
        if not isinstance(self.settings, dict):
            raise ValidationError("Settings must be a JSON object")

        # Check if required settings are present
        required_fields = ['pricing', 'timers']
        missing_fields = [field for field in required_fields if field not in self.settings]
        if missing_fields:
            raise ValidationError(f"Missing required settings: {', '.join(missing_fields)}")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class TemplateApplication(models.Model):
    """
    Model to track when templates are applied to devices
    """
    template = models.ForeignKey(ConfigurationTemplate, on_delete=models.CASCADE, related_name='applications')
    device = models.ForeignKey('devices.Device', on_delete=models.CASCADE, related_name='template_applications')
    applied_at = models.DateTimeField(auto_now_add=True)
    applied_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=[
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], default='success')
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ['-applied_at']
        verbose_name = "Template Application"
        verbose_name_plural = "Template Applications"

    def __str__(self):
        return f"Template {self.template.name} applied to {self.device.name}"