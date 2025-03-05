from rest_framework import serializers
from .models import Payment

class PaymentSerializer(serializers.ModelSerializer):
    """Serializes payment data for API responses."""
    class Meta:
        model = Payment
        fields = ['id', 'user', 'method', 'amount', 'status', 'created_at']
