from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

# Create your models here.

class Client(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, unique=True)
    card_id = models.CharField(max_length=50, unique=True)
    bonus_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.card_id})"

class BonusTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('accrual', 'Accrual'),
        ('redemption', 'Redemption'),
    )

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='bonus_transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount} for {self.client.name}"

    def save(self, *args, **kwargs):
        # Update client's bonus balance based on transaction type
        if self.transaction_type == 'accrual':
            self.client.bonus_balance += self.amount
        else:  # redemption
            if self.client.bonus_balance >= self.amount:
                self.client.bonus_balance -= self.amount
            else:
                raise ValueError("Insufficient bonus balance")
        
        self.client.save()
        super().save(*args, **kwargs)
