from django.contrib import admin
from .models import Client, BonusTransaction

class BonusTransactionInline(admin.TabularInline):
    model = BonusTransaction
    extra = 0
    readonly_fields = ['created_at']

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'card_id', 'bonus_balance', 'created_at']
    search_fields = ['name', 'phone', 'card_id']
    list_filter = ['created_at', 'updated_at']
    readonly_fields = ['bonus_balance', 'created_at', 'updated_at']
    inlines = [BonusTransactionInline]

@admin.register(BonusTransaction)
class BonusTransactionAdmin(admin.ModelAdmin):
    list_display = ['client', 'transaction_type', 'amount', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['client__name', 'client__phone', 'client__card_id', 'notes']
    readonly_fields = ['created_at']


