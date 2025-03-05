from django.db import models
from users.models import CustomUser


class Payment(models.Model):
    METHOD_CHOISE = [
        ('QR','QR'),
        ('Cash', 'Cash'),
        ('Card', 'Card')
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    method = models.CharField(max_length=20, choices=METHOD_CHOISE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)