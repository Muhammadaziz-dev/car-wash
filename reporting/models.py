# reporting/models.py
from django.db import models
import uuid
import os


def report_file_path(instance, filename):
    # Create a unique path for report files
    ext = filename.split('.')[-1]
    filename = f"{instance.id}_{uuid.uuid4()}.{ext}"
    return os.path.join('reports', filename)


class ReportJob(models.Model):
    REPORT_TYPES = (
        ('daily_revenue', 'Daily Revenue'),
        ('device_activity', 'Device Activity'),
        ('payment_summary', 'Payment Summary'),
        ('client_activity', 'Client Activity'),
        ('bonus_usage', 'Bonus Usage'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )

    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    parameters = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    excel_file = models.FileField(upload_to=report_file_path, null=True, blank=True)
    pdf_file = models.FileField(upload_to=report_file_path, null=True, blank=True)
    chart_file = models.FileField(upload_to=report_file_path, null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_report_type_display()} - {self.created_at}"

    def get_excel_url(self):
        if self.excel_file:
            return self.excel_file.url
        return None

    def get_pdf_url(self):
        if self.pdf_file:
            return self.pdf_file.url
        return None

    def get_chart_url(self):
        if self.chart_file:
            return self.chart_file.url
        return None
        
    def save(self, *args, **kwargs):
        """Clean up old files when updating"""
        if self.pk:
            try:
                # Get old instance
                old_instance = ReportJob.objects.get(pk=self.pk)
                
                # Check if files have changed
                if old_instance.excel_file and old_instance.excel_file != self.excel_file:
                    old_instance.excel_file.delete(False)
                if old_instance.pdf_file and old_instance.pdf_file != self.pdf_file:
                    old_instance.pdf_file.delete(False)
                if old_instance.chart_file and old_instance.chart_file != self.chart_file:
                    old_instance.chart_file.delete(False)
            except ReportJob.DoesNotExist:
                pass
                
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Delete associated files when deleting the model"""
        if self.excel_file:
            self.excel_file.delete(False)
        if self.pdf_file:
            self.pdf_file.delete(False)
        if self.chart_file:
            self.chart_file.delete(False)
            
        super().delete(*args, **kwargs)