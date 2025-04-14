from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Client, BonusTransaction
from .serializers import ClientSerializer, BonusTransactionSerializer

# Create your views here.

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Add filtering capabilities
        queryset = Client.objects.all()
        phone = self.request.query_params.get('phone', None)
        card_id = self.request.query_params.get('card_id', None)
        
        if phone:
            queryset = queryset.filter(phone__icontains=phone)
        if card_id:
            queryset = queryset.filter(card_id__icontains=card_id)
            
        return queryset

    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        client = self.get_object()
        transactions = client.bonus_transactions.all()
        serializer = BonusTransactionSerializer(transactions, many=True)
        return Response(serializer.data)

class BonusTransactionViewSet(viewsets.ModelViewSet):
    queryset = BonusTransaction.objects.all()
    serializer_class = BonusTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Add filtering capabilities
        queryset = BonusTransaction.objects.all()
        client_id = self.request.query_params.get('client_id', None)
        transaction_type = self.request.query_params.get('type', None)
        
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
            
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
