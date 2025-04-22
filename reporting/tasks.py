import logging
import traceback
from celery import shared_task
from .models import ReportJob
from .services import ReportService
from django.core.files import File
import os
import tempfile
import pandas as pd
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
# Remove WeasyPrint import temporarily
# from weasyprint import HTML, CSS
import base64
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server-side rendering
import matplotlib.pyplot as plt
from io import BytesIO

logger = logging.getLogger(__name__)

@shared_task
def generate_report(report_job_id):
    """Background task to generate a report"""
    report_job = ReportJob.objects.get(id=report_job_id)
    
    try:
        logger.info(f"Starting report generation: {report_job.report_type} (ID: {report_job.id})")
        report_job.status = 'processing'
        report_job.save()
        
        # Generate the report based on type
        if report_job.report_type == 'daily_revenue':
            result = ReportService.generate_daily_revenue_report(report_job.parameters)
        elif report_job.report_type == 'device_activity':
            result = ReportService.generate_device_activity_report(report_job.parameters)
        elif report_job.report_type == 'payment_summary':
            result = ReportService.generate_payment_summary_report(report_job.parameters)
        elif report_job.report_type == 'client_activity':
            result = ReportService.generate_client_activity_report(report_job.parameters)
        elif report_job.report_type == 'bonus_usage':
            result = ReportService.generate_bonus_usage_report(report_job.parameters)
        else:
            raise ValueError(f"Unsupported report type: {report_job.report_type}")
        
        # Save the report data to files
        _save_report_files(report_job, result)
        
        logger.info(f"Report generation completed: {report_job.report_type} (ID: {report_job.id})")
        report_job.status = 'completed'
        report_job.save()
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        logger.error(traceback.format_exc())
        report_job.status = 'failed'
        report_job.error_message = str(e)
        report_job.save()
        
        # Re-raise for Celery to handle the error
        raise

def _save_report_files(report_job, result):
    """Save report data to files"""
    # Create a temporary directory for report files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Base filename
        base_filename = f"{report_job.report_type}_{report_job.id}"
        
        # Save data to Excel if we have DataFrame(s)
        if 'data' in result and isinstance(result['data'], pd.DataFrame):
            excel_path = os.path.join(temp_dir, f"{base_filename}.xlsx")
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                # Write main data
                result['data'].to_excel(writer, sheet_name='Main Data', index=False)
                
                # Write additional dataframes if they exist
                for key, df in result.items():
                    if isinstance(df, pd.DataFrame) and key != 'data':
                        df.to_excel(writer, sheet_name=key.replace('_data', '').title(), index=False)
                
                # Write summary as a small table
                if 'summary' in result and isinstance(result['summary'], dict):
                    summary_df = pd.DataFrame([result['summary']])
                    summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Save Excel file to model
            with open(excel_path, 'rb') as f:
                report_job.excel_file.save(f"{base_filename}.xlsx", File(f))
        
        # Save chart image if it exists
        if 'chart' in result and result['chart']:
            chart_path = os.path.join(temp_dir, f"{base_filename}_chart.png")
            with open(chart_path, 'wb') as f:
                f.write(result['chart'].getvalue())
            
            # Save chart file to model
            with open(chart_path, 'rb') as f:
                report_job.chart_file.save(f"{base_filename}_chart.png", File(f))
        
        # Comment out PDF generation temporarily
        # _generate_pdf_report(report_job, result, temp_dir)

# Commenting out PDF generation temporarily
"""
def _generate_pdf_report(report_job, result, temp_dir):
    # Prepare chart for PDF if it exists
    chart_url = None
    if 'chart' in result and result['chart']:
        # Get chart data
        chart_data = result['chart'].getvalue()
        # Convert to base64 for embedding in HTML
        chart_b64 = base64.b64encode(chart_data).decode('utf-8')
        chart_url = f"data:image/png;base64,{chart_b64}"
    
    # Create a context for the template
    context = {
        'report': report_job,
        'report_name': report_job.get_report_type_display(),
        'summary': result.get('summary', {}),
        'chart_url': chart_url,
        'generated_at': timezone.now(),
    }
    
    # Add data tables to context if available
    data_tables = {}
    for key, value in result.items():
        if isinstance(value, pd.DataFrame) and not value.empty:
            # Convert DataFrame to HTML table
            data_tables[key.replace('_data', '').title()] = value.to_html(
                classes='table table-striped', 
                index=False,
                border=0
            )
    
    context['data_tables'] = data_tables
    
    try:
        # Render HTML template
        html_string = render_to_string('reporting/pdf_report.html', context)
        
        # Create a temporary file for the PDF
        pdf_path = os.path.join(temp_dir, f"{report_job.report_type}_{report_job.id}.pdf")
        
        # Base CSS for PDF styling
        css = CSS(string='''
            body { 
                font-family: Arial, sans-serif; 
                font-size: 12px;
                margin: 20px;
            }
            h1 { color: #333366; font-size: 20px; }
            h2 { color: #336699; font-size: 16px; margin-top: 20px; }
            table { width: 100%; border-collapse: collapse; margin: 15px 0; }
            th { background-color: #eeeeff; border: 1px solid #cccccc; padding: 8px; text-align: left; }
            td { border: 1px solid #cccccc; padding: 8px; }
            .summary-box { background-color: #f9f9f9; border: 1px solid #dddddd; padding: 15px; margin: 15px 0; }
            .footer { margin-top: 30px; border-top: 1px solid #cccccc; padding-top: 10px; font-size: 10px; color: #666666; }
        ''')
        
        # Convert HTML to PDF
        HTML(string=html_string).write_pdf(
            pdf_path, 
            stylesheets=[css]
        )
        
        # Save the PDF to the model
        with open(pdf_path, 'rb') as f:
            report_job.pdf_file.save(f"{report_job.report_type}_{report_job.id}.pdf", File(f))
            
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        logger.error(traceback.format_exc())
""" 