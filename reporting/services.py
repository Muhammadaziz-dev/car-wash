import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from django.db.models import Sum, Count, Avg, F, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import datetime, timedelta
from devices.models import Device, DeviceSession, DeviceLog
from loyalty.models import Client, BonusTransaction


class ReportService:
    @staticmethod
    def generate_daily_revenue_report(parameters):
        """Generate revenue report broken down by day"""
        start_date = parameters.get('start_date')
        end_date = parameters.get('end_date')
        device_ids = parameters.get('device_ids', [])
        
        # Convert string dates to datetime objects
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else timezone.now().date() - timedelta(days=30)
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else timezone.now().date()
        
        # Build query
        sessions = DeviceSession.objects.filter(
            started_at__date__gte=start_date,
            started_at__date__lte=end_date,
            status='completed'
        )
        
        if device_ids:
            sessions = sessions.filter(device_id__in=device_ids)
        
        # Annotate with date
        sessions = sessions.annotate(date=TruncDate('started_at'))
        
        # Aggregate data by day
        daily_data = (
            sessions.values('date')
            .annotate(
                total_revenue=Sum('amount_charged'),
                session_count=Count('id'),
                avg_session_time=Avg('total_duration')
            )
            .order_by('date')
        )
        
        # Convert to DataFrame for export
        df = pd.DataFrame(list(daily_data))
        
        # Add visualization
        chart_buffer = None
        if not df.empty and 'date' in df.columns and 'total_revenue' in df.columns:
            plt.figure(figsize=(10, 6))
            plt.bar(df['date'].astype(str), df['total_revenue'])
            plt.title('Daily Revenue')
            plt.xlabel('Date')
            plt.ylabel('Revenue')
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Save plot to BytesIO
            chart_buffer = BytesIO()
            plt.savefig(chart_buffer, format='png')
            chart_buffer.seek(0)
            plt.close()
        
        return {
            'data': df,
            'chart': chart_buffer,
            'summary': {
                'total_revenue': df['total_revenue'].sum() if not df.empty else 0,
                'total_sessions': df['session_count'].sum() if not df.empty else 0,
                'avg_session_time': df['avg_session_time'].mean() if not df.empty else 0,
                'date_range': f"{start_date} to {end_date}",
            }
        }

    @staticmethod
    def generate_device_activity_report(parameters):
        """Generate device activity report"""
        start_date = parameters.get('start_date')
        end_date = parameters.get('end_date')
        device_ids = parameters.get('device_ids', [])
        
        # Convert string dates to datetime objects
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else timezone.now().date() - timedelta(days=30)
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else timezone.now().date()
        
        # Get device sessions
        sessions_query = DeviceSession.objects.filter(
            started_at__date__gte=start_date,
            started_at__date__lte=end_date
        )
        
        if device_ids:
            sessions_query = sessions_query.filter(device_id__in=device_ids)
        
        # Get device logs
        logs_query = DeviceLog.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
        
        if device_ids:
            logs_query = logs_query.filter(device_id__in=device_ids)
        
        # Aggregate session data by device
        device_activity = (
            sessions_query.values('device__name', 'device_id')
            .annotate(
                total_sessions=Count('id'),
                total_duration=Sum('total_duration'),
                total_revenue=Sum('amount_charged'),
                avg_session_time=Avg('total_duration')
            )
            .order_by('-total_sessions')
        )
        
        # Aggregate log data by type
        log_summary = (
            logs_query.values('device__name', 'log_type')
            .annotate(
                count=Count('id')
            )
            .order_by('device__name', 'log_type')
        )
        
        # Convert to DataFrames
        df_activity = pd.DataFrame(list(device_activity))
        df_logs = pd.DataFrame(list(log_summary))
        
        # Create visualization
        chart_buffer = None
        if not df_activity.empty and 'device__name' in df_activity.columns and 'total_sessions' in df_activity.columns:
            plt.figure(figsize=(12, 6))
            plt.bar(df_activity['device__name'], df_activity['total_sessions'])
            plt.title('Device Activity - Total Sessions')
            plt.xlabel('Device')
            plt.ylabel('Number of Sessions')
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Save plot to BytesIO
            chart_buffer = BytesIO()
            plt.savefig(chart_buffer, format='png')
            chart_buffer.seek(0)
            plt.close()
        
        return {
            'device_data': df_activity,
            'log_data': df_logs,
            'chart': chart_buffer,
            'summary': {
                'total_devices': len(df_activity) if not df_activity.empty else 0,
                'total_sessions': df_activity['total_sessions'].sum() if not df_activity.empty else 0,
                'total_revenue': df_activity['total_revenue'].sum() if not df_activity.empty else 0,
                'date_range': f"{start_date} to {end_date}",
            }
        }

    @staticmethod
    def generate_payment_summary_report(parameters):
        """Generate payment summary report"""
        start_date = parameters.get('start_date')
        end_date = parameters.get('end_date')
        
        # Convert string dates to datetime objects
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else timezone.now().date() - timedelta(days=30)
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else timezone.now().date()
        
        # Get completed sessions with payments
        sessions = DeviceSession.objects.filter(
            started_at__date__gte=start_date,
            started_at__date__lte=end_date,
            status='completed',
            amount_charged__gt=0
        )
        
        # Aggregate payment data by day
        daily_payments = (
            sessions.annotate(date=TruncDate('started_at'))
            .values('date')
            .annotate(
                total_payments=Count('id'),
                total_amount=Sum('amount_charged'),
                avg_payment=Avg('amount_charged')
            )
            .order_by('date')
        )
        
        # Aggregate by device
        payment_by_device = (
            sessions.values('device__name')
            .annotate(
                total_payments=Count('id'),
                total_amount=Sum('amount_charged'),
                avg_payment=Avg('amount_charged')
            )
            .order_by('-total_amount')
        )
        
        # Convert to DataFrames
        df_daily = pd.DataFrame(list(daily_payments))
        df_by_device = pd.DataFrame(list(payment_by_device))
        
        # Create visualization
        chart_buffer = None
        if not df_daily.empty and 'date' in df_daily.columns and 'total_amount' in df_daily.columns:
            plt.figure(figsize=(12, 6))
            plt.plot(df_daily['date'].astype(str), df_daily['total_amount'], marker='o')
            plt.title('Daily Payment Summary')
            plt.xlabel('Date')
            plt.ylabel('Total Payments')
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Save plot to BytesIO
            chart_buffer = BytesIO()
            plt.savefig(chart_buffer, format='png')
            chart_buffer.seek(0)
            plt.close()
        
        return {
            'daily_data': df_daily,
            'device_data': df_by_device,
            'chart': chart_buffer,
            'summary': {
                'total_payments': df_daily['total_payments'].sum() if not df_daily.empty else 0,
                'total_amount': df_daily['total_amount'].sum() if not df_daily.empty else 0,
                'avg_payment': df_daily['avg_payment'].mean() if not df_daily.empty else 0,
                'date_range': f"{start_date} to {end_date}",
            }
        }

    @staticmethod
    def generate_client_activity_report(parameters):
        """Generate client activity report"""
        start_date = parameters.get('start_date')
        end_date = parameters.get('end_date')
        
        # Convert string dates to datetime objects
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else timezone.now().date() - timedelta(days=30)
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else timezone.now().date()
        
        # Get sessions with client cards
        sessions = DeviceSession.objects.filter(
            started_at__date__gte=start_date,
            started_at__date__lte=end_date,
            client_card__isnull=False
        ).exclude(client_card='')
        
        # Get clients
        clients = Client.objects.filter(
            created_at__date__lte=end_date
        )
        
        # Get bonus transactions
        bonus_transactions = BonusTransaction.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
        
        # Client activity from sessions
        client_activity = (
            sessions.values('client_card')
            .annotate(
                session_count=Count('id'),
                total_spent=Sum('amount_charged'),
                avg_session_time=Avg('total_duration')
            )
            .order_by('-session_count')
        )
        
        # New clients in period
        new_clients = (
            clients.filter(created_at__date__gte=start_date)
            .count()
        )
        
        # Bonus activity
        bonus_activity = (
            bonus_transactions.values('transaction_type')
            .annotate(
                transaction_count=Count('id'),
                total_amount=Sum('amount')
            )
        )
        
        # Convert to DataFrames
        df_activity = pd.DataFrame(list(client_activity))
        df_bonus = pd.DataFrame(list(bonus_activity))
        
        # Create visualization for client activity
        chart_buffer = None
        if not df_activity.empty and len(df_activity) > 0:
            # Limit to top 10 clients for better visualization
            if len(df_activity) > 10:
                df_plot = df_activity.head(10)
            else:
                df_plot = df_activity
                
            plt.figure(figsize=(12, 6))
            plt.bar(df_plot['client_card'], df_plot['session_count'])
            plt.title('Top Clients by Session Count')
            plt.xlabel('Client Card')
            plt.ylabel('Number of Sessions')
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Save plot to BytesIO
            chart_buffer = BytesIO()
            plt.savefig(chart_buffer, format='png')
            chart_buffer.seek(0)
            plt.close()
        
        # Calculate bonus summary
        total_accrued = 0
        total_redeemed = 0
        
        if not df_bonus.empty:
            # Sum accruals
            accruals = df_bonus[df_bonus['transaction_type'] == 'accrual']
            if not accruals.empty:
                total_accrued = accruals['total_amount'].sum()
                
            # Sum redemptions
            redemptions = df_bonus[df_bonus['transaction_type'] == 'redemption']
            if not redemptions.empty:
                total_redeemed = redemptions['total_amount'].sum()
        
        return {
            'client_data': df_activity,
            'bonus_data': df_bonus,
            'chart': chart_buffer,
            'summary': {
                'total_clients': clients.count(),
                'new_clients': new_clients,
                'active_clients': len(df_activity) if not df_activity.empty else 0,
                'total_bonus_accrued': total_accrued,
                'total_bonus_redeemed': total_redeemed,
                'date_range': f"{start_date} to {end_date}",
            }
        }

    @staticmethod
    def generate_bonus_usage_report(parameters):
        """Generate bonus usage report"""
        start_date = parameters.get('start_date')
        end_date = parameters.get('end_date')
        
        # Convert string dates to datetime objects
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else timezone.now().date() - timedelta(days=30)
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else timezone.now().date()
        
        # Get bonus transactions
        transactions = BonusTransaction.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
        
        # Daily aggregation
        daily_transactions = (
            transactions.annotate(date=TruncDate('created_at'))
            .values('date', 'transaction_type')
            .annotate(
                transaction_count=Count('id'),
                total_amount=Sum('amount')
            )
            .order_by('date', 'transaction_type')
        )
        
        # Client aggregation
        client_transactions = (
            transactions.values('client__name', 'client_id', 'transaction_type')
            .annotate(
                transaction_count=Count('id'),
                total_amount=Sum('amount')
            )
            .order_by('client_id', 'transaction_type')
        )
        
        # Convert to DataFrames
        df_daily = pd.DataFrame(list(daily_transactions))
        df_client = pd.DataFrame(list(client_transactions))
        
        # Create chart - comparing accruals and redemptions by date
        chart_buffer = None
        if not df_daily.empty:
            # Pivot the data to have accruals and redemptions as separate columns
            pivot_data = pd.pivot_table(
                df_daily, 
                values='total_amount', 
                index='date', 
                columns='transaction_type', 
                aggfunc='sum'
            ).fillna(0)
            
            # Make the plot
            plt.figure(figsize=(12, 6))
            
            # If we have both accruals and redemptions
            if 'accrual' in pivot_data.columns and 'redemption' in pivot_data.columns:
                plt.plot(pivot_data.index, pivot_data['accrual'], 'g-', label='Accruals')
                plt.plot(pivot_data.index, pivot_data['redemption'], 'r-', label='Redemptions')
                plt.title('Bonus Points: Accruals vs Redemptions')
                plt.legend()
            # If we only have accruals
            elif 'accrual' in pivot_data.columns:
                plt.plot(pivot_data.index, pivot_data['accrual'], 'g-', label='Accruals')
                plt.title('Bonus Points: Accruals')
                plt.legend()
            # If we only have redemptions
            elif 'redemption' in pivot_data.columns:
                plt.plot(pivot_data.index, pivot_data['redemption'], 'r-', label='Redemptions')
                plt.title('Bonus Points: Redemptions')
                plt.legend()
            
            plt.xlabel('Date')
            plt.ylabel('Amount')
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Save plot to BytesIO
            chart_buffer = BytesIO()
            plt.savefig(chart_buffer, format='png')
            chart_buffer.seek(0)
            plt.close()
        
        # Summary calculations
        accrual_totals = transactions.filter(transaction_type='accrual').aggregate(
            total=Sum('amount'), count=Count('id'))
        redemption_totals = transactions.filter(transaction_type='redemption').aggregate(
            total=Sum('amount'), count=Count('id'))
        
        return {
            'daily_data': df_daily,
            'client_data': df_client,
            'chart': chart_buffer,
            'summary': {
                'total_accrued': accrual_totals['total'] or 0,
                'accrual_count': accrual_totals['count'] or 0,
                'total_redeemed': redemption_totals['total'] or 0,
                'redemption_count': redemption_totals['count'] or 0,
                'net_change': (accrual_totals['total'] or 0) - (redemption_totals['total'] or 0),
                'date_range': f"{start_date} to {end_date}",
            }
        }