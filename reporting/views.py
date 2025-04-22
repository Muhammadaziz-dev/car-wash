from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import ReportJob
from .serializers import ReportJobSerializer
from .tasks import generate_report


class ReportJobViewSet(viewsets.ModelViewSet):
    queryset = ReportJob.objects.all()
    serializer_class = ReportJobSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter reports by user unless admin"""
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return ReportJob.objects.all()
        return ReportJob.objects.filter(created_by=user)

    def perform_create(self, serializer):
        """Create a report job and trigger async generation"""
        report_job = serializer.save(created_by=self.request.user, status='pending')
        
        # Start the Celery task
        generate_report.delay(report_job.id)
        
    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        """Regenerate a report with the same parameters"""
        report_job = self.get_object()
        
        # Update status and clear previous files/errors
        report_job.status = 'pending'
        report_job.error_message = None
        
        # Delete old files if they exist
        if hasattr(report_job, 'excel_file') and report_job.excel_file:
            report_job.excel_file.delete()
        if hasattr(report_job, 'pdf_file') and report_job.pdf_file:
            report_job.pdf_file.delete()
        if hasattr(report_job, 'chart_file') and report_job.chart_file:
            report_job.chart_file.delete()
            
        report_job.save()
        
        # Start the Celery task
        generate_report.delay(report_job.id)
        
        return Response(self.get_serializer(report_job).data)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Get download links for a report's files"""
        report_job = self.get_object()

        if report_job.status != 'completed':
            return Response(
                {"error": "Report not completed yet", "status": report_job.status},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        response_data = {
            "status": report_job.status,
            "files": {}
        }
        
        if report_job.excel_file:
            response_data["files"]["excel"] = request.build_absolute_uri(report_job.excel_file.url)
            
        if report_job.pdf_file:
            response_data["files"]["pdf"] = request.build_absolute_uri(report_job.pdf_file.url)
            
        if report_job.chart_file:
            response_data["files"]["chart"] = request.build_absolute_uri(report_job.chart_file.url)
            
        if not response_data["files"]:
            return Response(
                {"error": "No files available for this report"},
                status=status.HTTP_404_NOT_FOUND
            )
            
        return Response(response_data)
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Check the status of a report job"""
        report_job = self.get_object()
        
        response_data = {
            "id": report_job.id,
            "report_type": report_job.report_type,
            "status": report_job.status,
            "created_at": report_job.created_at,
            "updated_at": report_job.updated_at
        }
        
        if report_job.status == 'failed' and report_job.error_message:
            response_data["error_message"] = report_job.error_message
            
        return Response(response_data)
