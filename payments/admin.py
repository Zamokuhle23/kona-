from django.contrib import admin
from .models import Merchant, Customer, CreditCard, CreditStatement, CreditTransaction, PaymentSession, Repayment


@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = ['name', 'business_type', 'phone', 'location', 'is_active', 'created_at']
    list_filter = ['is_active', 'business_type']
    search_fields = ['name', 'phone']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone', 'bank', 'credit_limit', 'current_balance', 'available_credit', 'created_at']
    list_filter = ['bank', 'is_active', 'default_funding_mode']
    search_fields = ['full_name', 'phone']
    readonly_fields = ['available_credit', 'minimum_payment', 'days_until_due']


@admin.register(CreditCard)
class CreditCardAdmin(admin.ModelAdmin):
    list_display = ['customer', 'masked_number', 'expiry_formatted', 'status', 'bin_country', 'created_at']
    list_filter = ['status', 'bin_country']
    readonly_fields = ['masked_number', 'expiry_formatted']


@admin.register(CreditStatement)
class CreditStatementAdmin(admin.ModelAdmin):
    list_display = ['customer', 'period_start', 'period_end', 'due_date', 'closing_balance', 'minimum_payment', 'status']
    list_filter = ['status']


@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = ['customer', 'transaction_type', 'funding_source', 'amount', 'merchant', 'created_at']
    list_filter = ['transaction_type', 'funding_source']
    search_fields = ['customer__phone', 'merchant__name']


@admin.register(PaymentSession)
class PaymentSessionAdmin(admin.ModelAdmin):
    list_display = ['merchant', 'amount', 'status', 'funding_source', 'bank_used', 'created_at']
    list_filter = ['status', 'funding_source']
    readonly_fields = ['id', 'created_at', 'confirmed_at']


@admin.register(Repayment)
class RepaymentAdmin(admin.ModelAdmin):
    list_display = ['customer', 'amount', 'method', 'status', 'created_at']
    list_filter = ['method', 'status']