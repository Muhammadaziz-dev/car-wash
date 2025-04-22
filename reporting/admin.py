from django.contrib import admin
from django.utils.html import format_html
from .models import ReportJob

@admin.register(ReportJob)
class ReportJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'report_type', 'status', 'created_by', 'created_at', 'file_links']
    list_filter = ['report_type', 'status', 'created_at']
    search_fields = ['report_type', 'created_by__username']
    readonly_fields = ['status', 'error_message', 'created_at', 'updated_at', 'file_links']
    fieldsets = (
        (None, {
            'fields': ('report_type', 'parameters', 'status', 'created_by')
        }),
        ('Files', {
            'fields': ('excel_file', 'pdf_file', 'chart_file', 'file_links'),
            'classes': ('collapse',),
        }),
        ('Details', {
            'fields': ('error_message', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def file_links(self, obj):
        """Display download links for report files"""
        links = []
        
        if obj.excel_file:
            links.append(format_html('<a href="{}" target="_blank">Excel</a>', obj.excel_file.url))
            
        if obj.pdf_file:
            links.append(format_html('<a href="{}" target="_blank">PDF</a>', obj.pdf_file.url))
            
        if obj.chart_file:
            links.append(format_html('<a href="{}" target="_blank">Chart</a>', obj.chart_file.url))
            
        if links:
            return format_html(' | '.join(links))
        return "-"
    
    file_links.short_description = "Download"
    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj and obj.status in ['completed', 'failed']:
            readonly.extend(['report_type', 'parameters'])
        return readonly