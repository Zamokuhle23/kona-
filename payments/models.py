from django.db import models
from django.utils import timezone
import uuid
import random


def generate_card_number():
    return '4' + ''.join([str(random.randint(0, 9)) for _ in range(15)])


def generate_cvv():
    return ''.join([str(random.randint(0, 9)) for _ in range(3)])


def default_expiry():
    return timezone.now().date().replace(year=timezone.now().year + 3)


class Merchant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    business_type = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, unique=True)
    location = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']


class Customer(models.Model):
    BANK_CHOICES = [
        ('fnb', 'FNB Eswatini'),
        ('standard', 'Standard Bank'),
        ('nedbank', 'Nedbank'),
        ('eswatini_bank', 'Eswatini Bank'),
    ]
    FUNDING_MODE_CHOICES = [
        ('kona_credit', 'Kona Credit Card'),
        ('bank', 'Bank Account (EPS)'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=200, blank=True)
    national_id = models.CharField(max_length=50, blank=True)
    bank = models.CharField(max_length=100, blank=True, choices=BANK_CHOICES)
    default_funding_mode = models.CharField(max_length=20, choices=FUNDING_MODE_CHOICES, default='kona_credit')

    credit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=2000.00)
    current_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    statement_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_due_date = models.DateField(null=True, blank=True)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=24.00)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def available_credit(self):
        from decimal import Decimal
        return self.credit_limit - self.current_balance

    @property
    def minimum_payment(self):
        from decimal import Decimal
        if self.statement_balance <= 0:
            return Decimal('0.00')
        return max(self.statement_balance * Decimal('0.10'), Decimal('50.00'))

    @property
    def days_until_due(self):
        if not self.payment_due_date:
            return None
        return (self.payment_due_date - timezone.now().date()).days

    @property
    def is_overdue(self):
        if not self.payment_due_date:
            return False
        return timezone.now().date() > self.payment_due_date and self.statement_balance > 0

    def __str__(self):
        return f"{self.full_name or self.phone}"

    class Meta:
        ordering = ['-created_at']


class CardDetails(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('frozen', 'Frozen'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending Activation'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='card_details')
    card_number = models.CharField(max_length=16, default=generate_card_number)
    cvv = models.CharField(max_length=3, default=generate_cvv)
    expiry_date = models.DateField(default=default_expiry)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    bin_country = models.CharField(max_length=50, default='ZA')
    card_network = models.CharField(max_length=20, default='Visa')
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def masked_number(self):
        return f"**** **** **** {self.card_number[-4:]}"

    @property
    def expiry_display(self):
        return self.expiry_date.strftime('%m/%y')

    @property
    def expiry_month(self):
        return self.expiry_date.month

    @property
    def expiry_year(self):
        return self.expiry_date.year

    def __str__(self):
        return f"{self.customer} — {self.masked_number}"


class CreditStatement(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed — Unpaid'),
        ('paid_minimum', 'Minimum Paid'),
        ('paid_full', 'Paid in Full'),
        ('overdue', 'Overdue'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='statements')
    period_start = models.DateField()
    period_end = models.DateField()
    due_date = models.DateField()
    opening_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_purchases = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_payments = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    interest_charged = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    closing_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    minimum_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def days_until_due(self):
        return (self.due_date - timezone.now().date()).days

    def __str__(self):
        return f"{self.customer} — {self.period_start} to {self.period_end} — {self.status}"

    class Meta:
        ordering = ['-period_end']


class CreditTransaction(models.Model):
    TYPE_CHOICES = [
        ('purchase', 'Purchase'),
        ('repayment', 'Repayment'),
        ('interest', 'Interest Charge'),
        ('fee', 'Fee'),
        ('refund', 'Refund'),
    ]
    FUNDING_CHOICES = [
        ('credit', 'Kona Credit'),
        ('bank', 'Bank Transfer (EPS)'),
        ('jit', 'JIT Bank to Card'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='credit_transactions')
    merchant = models.ForeignKey(Merchant, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    statement = models.ForeignKey(CreditStatement, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    session = models.ForeignKey('PaymentSession', on_delete=models.SET_NULL, null=True, blank=True, related_name='credit_transactions')
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    funding_mode = models.CharField(max_length=30, choices=FUNDING_CHOICES, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=300, blank=True)
    reference = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer} — {self.transaction_type} — E{self.amount}"

    class Meta:
        ordering = ['-created_at']


class PaymentSession(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('waiting', 'Waiting for Customer'),
        ('confirmed', 'Confirmed'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    ]
    FUNDING_CHOICES = [
        ('credit', 'Kona Credit Card'),
        ('bank', 'Bank Transfer (EPS)'),
        ('jit', 'JIT Bank to Card'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='sessions')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    funding_mode = models.CharField(max_length=30, choices=FUNDING_CHOICES, blank=True)
    bank_used = models.CharField(max_length=100, blank=True)
    jit_funded = models.BooleanField(default=False)
    jit_bank = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.merchant.name} — E{self.amount} — {self.status}"

    class Meta:
        ordering = ['-created_at']


class DebitMandate(models.Model):
    BANK_CHOICES = [
        ('fnb', 'FNB Eswatini'),
        ('standard', 'Standard Bank'),
        ('nedbank', 'Nedbank'),
        ('eswatini_bank', 'Eswatini Bank'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('suspended', 'Suspended'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='mandates')
    bank = models.CharField(max_length=100, choices=BANK_CHOICES)
    account_number = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    authorised_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer} — {self.bank} — {self.status}"

    class Meta:
        ordering = ['-authorised_at']


class Repayment(models.Model):
    METHOD_CHOICES = [
        ('eps_transfer', 'EPS Bank Transfer'),
        ('debit_order', 'Debit Order'),
        ('cash', 'Cash at Branch'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='repayments')
    statement = models.ForeignKey(CreditStatement, on_delete=models.SET_NULL, null=True, blank=True, related_name='repayments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='eps_transfer')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reference = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.customer} — E{self.amount} — {self.status}"

    class Meta:
        ordering = ['-created_at']


class CreditCard(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('frozen', 'Frozen'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending Activation'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='credit_cards')
    card_number = models.CharField(max_length=16, default=generate_card_number)
    cvv = models.CharField(max_length=3, default=generate_cvv)
    expiry_date = models.DateField(default=default_expiry)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    bin_country = models.CharField(max_length=50, default='ZA')
    card_network = models.CharField(max_length=20, default='Visa')
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def masked_number(self):
        return f"**** **** **** {self.card_number[-4:]}"

    @property
    def expiry_formatted(self):
        return self.expiry_date.strftime('%m/%y')

    def __str__(self):
        return f"{self.customer} — {self.masked_number}"

