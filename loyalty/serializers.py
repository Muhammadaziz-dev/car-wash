from rest_framework import serializers
from .models import Client, BonusTransaction
from decimal import Decimal

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name', 'phone', 'card_id', 'bonus_balance', 'created_at', 'updated_at']
        read_only_fields = ['bonus_balance', 'created_at', 'updated_at']

    def validate_phone(self, value):
        # Add phone number validation if needed
        return value

    def validate_card_id(self, value):
        # Add card ID validation if needed
        return value

class BonusTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BonusTransaction
        fields = ['id', 'client', 'transaction_type', 'amount', 'notes', 'created_at']
        read_only_fields = ['created_at']

    def validate_amount(self, value):
        if value <= Decimal('0.00'):
            raise serializers.ValidationError("Amount must be greater than zero")
        return value

    def validate(self, data):
        # Check if client has sufficient balance for redemption
        if data['transaction_type'] == 'redemption':
            client = data['client']
            if client.bonus_balance < data['amount']:
                raise serializers.ValidationError("Insufficient bonus balance")
        return data 