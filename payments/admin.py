from django.contrib import admin
from .models import Merchant, Customer, CardDetails, CreditStatement, CreditTransaction, PaymentSession, DebitMandate


@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = ['name', 'business_type', 'phone', 'location', 'is_active', 'created_at']
    list_filter = ['is_active', 'business_type']
    search_fields = ['name', 'phone']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone', 'bank', 'credit_limit', 'current_balance', 'available_credit', 'is_overdue', 'created_at']
    list_filter = ['bank', 'is_active', 'default_funding_mode']
    search_fields = ['full_name', 'phone']
    readonly_fields = ['available_credit', 'minimum_payment', 'is_overdue']


@admin.register(CardDetails)
class CardDetailsAdmin(admin.ModelAdmin):
    list_display = ['customer', 'masked_number', 'expiry_display', 'status', 'bin_country', 'created_at']
    list_filter = ['status', 'bin_country']
    readonly_fields = ['masked_number', 'expiry_display']


@admin.register(CreditStatement)
class CreditStatementAdmin(admin.ModelAdmin):
    list_display = ['customer', 'period_start', 'period_end', 'due_date', 'closing_balance', 'minimum_payment', 'status']
    list_filter = ['status']
    readonly_fields = ['days_until_due']


@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = ['customer', 'transaction_type', 'funding_mode', 'amount', 'merchant', 'created_at']
    list_filter = ['transaction_type', 'funding_mode']
    search_fields = ['customer__phone', 'merchant__name']


@admin.register(PaymentSession)
class PaymentSessionAdmin(admin.ModelAdmin):
    list_display = ['merchant', 'amount', 'status', 'funding_mode', 'bank_used', 'jit_funded', 'created_at']
    list_filter = ['status', 'funding_mode']
    readonly_fields = ['id', 'created_at', 'confirmed_at']


@admin.register(DebitMandate)
class DebitMandateAdmin(admin.ModelAdmin):
    list_display = ['customer', 'bank', 'status', 'authorised_at']
    list_filter = ['bank', 'status']
