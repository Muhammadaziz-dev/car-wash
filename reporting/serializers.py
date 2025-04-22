from rest_framework import serializers
from reporting.models import ReportJob


class ReportJobSerializer(serializers.ModelSerializer):
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    excel_url = serializers.SerializerMethodField()
    pdf_url = serializers.SerializerMethodField()
    chart_url = serializers.SerializerMethodField()

    class Meta:
        model = ReportJob
        fields = ['id', 'report_type', 'parameters', 'status', 
                  'excel_url', 'pdf_url', 'chart_url', 'error_message', 
                  'created_at', 'updated_at', 'created_by']
        read_only_fields = ['status', 'excel_url', 'pdf_url', 'chart_url', 
                           'error_message', 'created_at', 'updated_at']

    def get_excel_url(self, obj):
        request = self.context.get('request')
        if obj.excel_file and hasattr(obj.excel_file, 'url'):
            return request.build_absolute_uri(obj.excel_file.url) if request else obj.excel_file.url
        return None
    
    def get_pdf_url(self, obj):
        request = self.context.get('request')
        if obj.pdf_file and hasattr(obj.pdf_file, 'url'):
            return request.build_absolute_uri(obj.pdf_file.url) if request else obj.pdf_file.url
        return None
    
    def get_chart_url(self, obj):
        request = self.context.get('request')
        if obj.chart_file and hasattr(obj.chart_file, 'url'):
            return request.build_absolute_uri(obj.chart_file.url) if request else obj.chart_file.url
        return None