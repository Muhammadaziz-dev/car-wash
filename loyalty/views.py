from decimal import Decimal
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from django.db import transaction
from rest_framework.response import Response

from accounts.permissions import (
    IsOperatorOrReadOnly,
    IsOperator,
    IsViewer,
)
from .models import Client, BonusTransaction
from .serializers import ClientSerializer, BonusTransactionSerializer

# Define static bonus rules: recharge ≥ 100  →  +10 points
BONUS_RULES = [
    (Decimal('100.00'), Decimal('10.00')),
]

class ClientViewSet(viewsets.ModelViewSet):
    """
    CRUD for clients, plus custom actions:
    - GET /clients/{pk}/transactions/
    - POST /clients/{pk}/recharge/
    """
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [IsOperatorOrReadOnly]  # viewers read, operators/admins write :contentReference[oaicite:0]{index=0}

    def get_queryset(self):
        queryset = super().get_queryset()
        phone = self.request.query_params.get('phone')
        card_id = self.request.query_params.get('card_id')
        if phone:
            queryset = queryset.filter(phone__icontains=phone)
        if card_id:
            queryset = queryset.filter(card_id__icontains=card_id)
        return queryset

    @action(detail=True, methods=['get'], permission_classes=[IsViewer])
    def transactions(self, request, pk=None):
        """List all bonus transactions for this client."""
        client = self.get_object()
        txns = client.bonus_transactions.all()
        serializer = BonusTransactionSerializer(txns, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsOperator])
    def recharge(self, request, pk=None):
        """
        Process a recharge:
         1. Always accrual a transaction for the raw amount.
         2. If amount ≥ threshold, award extra bonus points.
        """
        client = get_object_or_404(Client, pk=pk)  # safe fetch :contentReference[oaicite:1]{index=1}
        # Parse & validate amount
        try:
            amount = Decimal(request.data.get('amount', '0'))
        except Exception:
            return Response({"error": "Invalid amount."}, status=status.HTTP_400_BAD_REQUEST)
        if amount <= 0:
            return Response({"error": "Amount must be positive."}, status=status.HTTP_400_BAD_REQUEST)

        # 1️⃣ Base accrual
        base_txn = BonusTransaction(
            client=client,
            transaction_type='accrual',
            amount=amount,
            notes=f"Recharge of {amount}"
        )
        base_txn.save()  # updates client.bonus_balance via model save

        # 2️⃣ Threshold bonus
        bonus_awarded = Decimal('0.00')
        for threshold, bonus in BONUS_RULES:
            if amount >= threshold:
                bonus_awarded = bonus
                bonus_txn = BonusTransaction(
                    client=client,
                    transaction_type='accrual',
                    amount=bonus,
                    notes=f"Bonus for recharge ≥ {threshold}"
                )
                bonus_txn.save()
                break

        # 3️⃣ Respond with updated client
        serializer = ClientSerializer(client, context={'request': request})
        return Response({
            "client": serializer.data,
            "recharge_amount": str(amount),
            "bonus_awarded": str(bonus_awarded)
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def recharge(self, request, pk=None):
        """
        Process a recharge and award bonus points based on thresholds.

        Thresholds:
        - Recharge ≥ 100 units: +10 bonus points
        - Recharge ≥ 200 units: +25 bonus points
        - Recharge ≥ 500 units: +75 bonus points
        """
        client = self.get_object()

        # Validate amount
        try:
            amount = Decimal(request.data.get('amount', 0))
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid amount format"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if amount <= 0:
            return Response(
                {"error": "Amount must be greater than zero"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Optional device_id and notes
        device_id = request.data.get('device_id')
        notes = request.data.get('notes', '')

        # Determine bonus based on threshold
        bonus = Decimal('0.00')
        if amount >= 500:
            bonus = Decimal('75.00')
        elif amount >= 200:
            bonus = Decimal('25.00')
        elif amount >= 100:
            bonus = Decimal('10.00')

        # Record the transaction and bonus (if applicable)
        transaction_note = f"Recharge: {amount}"
        if device_id:
            transaction_note += f", Device: {device_id}"
        if notes:
            transaction_note += f", Notes: {notes}"

        # Award bonus if applicable
        if bonus > 0:
            BonusTransaction.objects.create(
                client=client,
                transaction_type='accrual',
                amount=bonus,
                notes=f"Bonus for {amount} recharge"
            )

        # Refresh client to get updated balance
        client.refresh_from_db()

        return Response({
            "success": True,
            "recharge_amount": amount,
            "bonus_awarded": bonus,
            "current_bonus_balance": client.bonus_balance,
            "message": f"Recharge of {amount} processed successfully"
        })


class BonusTransactionViewSet(viewsets.ModelViewSet):
    """
    CRUD for bonus transactions; read-only for viewers.
    """
    queryset = BonusTransaction.objects.all()
    serializer_class = BonusTransactionSerializer
    permission_classes = [IsOperatorOrReadOnly]  # viewers read, operators/admins write :contentReference[oaicite:2]{index=2}

    def get_queryset(self):
        queryset = super().get_queryset()
        client_id = self.request.query_params.get('client_id')
        txn_type = self.request.query_params.get('type')
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        if txn_type:
            queryset = queryset.filter(transaction_type=txn_type)
        return queryset
