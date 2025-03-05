from celery import shared_task
from django.utils import timezone
from .models import ServiceUsage
from users.models import CustomUser


@shared_task
def deduct_balance(usage_id):
    try:
        usage = ServiceUsage.objects.get(id=usage_id)
    except ServiceUsage.DoesNotExist:
        return

    if not usage.is_active:
        return

    user = usage.user
    service = usage.service
    interval = 5 # 5 sec deduct
    amount = service.rate_per_second * interval

    if user.balance >= amount:
        user.balance -= amount
        usage.total_cost += amount
        user.save()
        usage.save()

        deduct_balance.apply_async((usage_id, ), countdown=interval)
    else:
        usage.is_active = False
        usage.end_time = timezone.now()
        usage.save()
