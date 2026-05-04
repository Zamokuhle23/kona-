from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from decimal import Decimal
from datetime import timedelta

from .models import (
    Merchant, Customer, CardDetails, CreditStatement,
    CreditTransaction, PaymentSession, DebitMandate
)
from .serializers import (
    MerchantSerializer, CustomerSerializer, CardDetailsFullSerializer,
    CreditStatementSerializer, CreditTransactionSerializer,
    PaymentSessionSerializer, DebitMandateSerializer,
    CreateSessionSerializer, ConfirmPaymentSerializer,
    RepaymentSerializer, FreezeCardSerializer,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def session_response(session, merchant=None):
    m = merchant or session.merchant
    return {
        'session_id': str(session.id),
        'merchant_id': str(m.id),
        'merchant_name': m.name,
        'merchant_location': m.location,
        'amount': str(session.amount),
        'status': session.status,
        'funding_mode': session.funding_mode,
        'qr_url': f'/m/{m.id}/{session.id}',
    }


def get_or_create_card(customer):
    card, _ = CardDetails.objects.get_or_create(customer=customer)
    return card


def get_open_statement(customer):
    today = timezone.now().date()
    stmt = CreditStatement.objects.filter(
        customer=customer, status='open'
    ).first()
    if not stmt:
        period_start = today.replace(day=1)
        if today.month == 12:
            period_end = today.replace(year=today.year+1, month=1, day=1) - timedelta(days=1)
        else:
            period_end = today.replace(month=today.month+1, day=1) - timedelta(days=1)
        due_date = period_end + timedelta(days=15)
        stmt = CreditStatement.objects.create(
            customer=customer,
            period_start=period_start,
            period_end=period_end,
            due_date=due_date,
            opening_balance=customer.current_balance,
        )
    return stmt


# ── Merchants ─────────────────────────────────────────────────────────────────

class MerchantListView(APIView):
    def get(self, request):
        merchants = Merchant.objects.filter(is_active=True)
        return Response(MerchantSerializer(merchants, many=True).data)

    def post(self, request):
        serializer = MerchantSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MerchantDetailView(APIView):
    def get(self, request, pk):
        merchant = get_object_or_404(Merchant, pk=pk)
        return Response(MerchantSerializer(merchant).data)


# ── Customers ─────────────────────────────────────────────────────────────────

class CustomerListView(APIView):
    def get(self, request):
        customers = Customer.objects.filter(is_active=True)
        return Response(CustomerSerializer(customers, many=True).data)

    def post(self, request):
        serializer = CustomerSerializer(data=request.data)
        if serializer.is_valid():
            customer = serializer.save()
            get_or_create_card(customer)
            return Response(CustomerSerializer(customer).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomerDetailView(APIView):
    def get(self, request, phone):
        customer = get_object_or_404(Customer, phone=phone)
        get_or_create_card(customer)
        return Response(CustomerSerializer(customer).data)


# ── Card ──────────────────────────────────────────────────────────────────────

class CardDetailView(APIView):
    """Get full card details for the logged-in customer."""
    def get(self, request, phone):
        customer = get_object_or_404(Customer, phone=phone)
        card = get_or_create_card(customer)
        return Response(CardDetailsFullSerializer(card).data)


class FreezeCardView(APIView):
    def post(self, request):
        serializer = FreezeCardSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        customer = get_object_or_404(Customer, phone=serializer.validated_data['customer_phone'])
        card = get_or_create_card(customer)
        action = serializer.validated_data['action']
        card.status = 'frozen' if action == 'freeze' else 'active'
        card.save()
        return Response({'status': card.status, 'message': f'Card {action}d successfully.'})


# ── Payment Sessions ──────────────────────────────────────────────────────────

class CreateSessionView(APIView):
    def post(self, request):
        serializer = CreateSessionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        merchant = get_object_or_404(Merchant, pk=serializer.validated_data['merchant_id'])

        # Cancel existing pending sessions for this merchant
        PaymentSession.objects.filter(
            merchant=merchant, status='waiting'
        ).update(status='expired')

        session = PaymentSession.objects.create(
            merchant=merchant,
            amount=serializer.validated_data['amount'],
            status='waiting',
        )
        return Response(session_response(session, merchant), status=status.HTTP_201_CREATED)


class SessionDetailView(APIView):
    def get(self, request, session_id):
        session = get_object_or_404(PaymentSession, pk=session_id)
        return Response(session_response(session))


class MerchantLatestSessionView(APIView):
    def get(self, request, merchant_id):
        merchant = get_object_or_404(Merchant, pk=merchant_id)
        cutoff = timezone.now() - timezone.timedelta(minutes=10)
        session = PaymentSession.objects.filter(
            merchant=merchant,
            status='waiting',
            created_at__gte=cutoff,
        ).order_by('-created_at').first()

        if session:
            return Response({
                'has_pending': True,
                'session': session_response(session, merchant),
                'merchant': MerchantSerializer(merchant).data,
            })
        return Response({
            'has_pending': False,
            'session': None,
            'merchant': MerchantSerializer(merchant).data,
        })


class ConfirmPaymentView(APIView):
    def post(self, request):
        serializer = ConfirmPaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        session = get_object_or_404(PaymentSession, pk=data['session_id'])

        if session.status == 'confirmed':
            return Response({'error': 'This payment has already been confirmed.'}, status=400)
        if session.status == 'expired':
            return Response({'error': 'This session has expired. Please scan again.'}, status=400)

        customer, _ = Customer.objects.get_or_create(
            phone=data['customer_phone'],
            defaults={'default_funding_mode': data['funding_mode']}
        )
        get_or_create_card(customer)

        funding_mode = data['funding_mode']
        amount = session.amount

        # ── Credit card payment ───────────────────────────────────────────
        if funding_mode == 'credit':
            card = customer.card
            if card.status == 'frozen':
                return Response({'error': 'Your Kona card is frozen.'}, status=400)
            if customer.available_credit < amount:
                return Response({
                    'error': f'Insufficient credit. Available: E{customer.available_credit}'
                }, status=400)

            # Debit credit balance
            customer.current_balance += amount
            customer.save()

            # Record on statement
            stmt = get_open_statement(customer)
            stmt.total_purchases += amount
            stmt.closing_balance = customer.current_balance
            stmt.save()

            # Create credit transaction
            CreditTransaction.objects.create(
                customer=customer,
                transaction_type='purchase',
                funding_mode='credit',
                amount=amount,
                session=session,
                merchant=session.merchant,
                statement=stmt,
                description=f'Purchase at {session.merchant.name}',
            )

            session.funding_mode = 'credit'

        # ── Bank transfer (EPS) ───────────────────────────────────────────
        elif funding_mode == 'bank':
            bank = data.get('bank', '')
            if not bank:
                return Response({'error': 'Bank is required for bank transfer.'}, status=400)
            session.bank_used = bank
            session.funding_mode = 'bank'

            # Create credit transaction record (no balance change — direct transfer)
            CreditTransaction.objects.create(
                customer=customer,
                transaction_type='purchase',
                funding_mode='bank',
                amount=amount,
                session=session,
                merchant=session.merchant,
                description=f'EPS transfer at {session.merchant.name} via {bank.upper()}',
            )

        # ── JIT — bank funds card in real time ───────────────────────────
        elif funding_mode == 'jit':
            jit_bank = data.get('jit_bank', '')
            if not jit_bank:
                return Response({'error': 'JIT bank is required.'}, status=400)

            # Simulate JIT pull — in production this calls EPS debit API
            session.jit_funded = True
            session.jit_bank = jit_bank
            session.funding_mode = 'jit'

            CreditTransaction.objects.create(
                customer=customer,
                transaction_type='purchase',
                funding_mode='jit',
                amount=amount,
                session=session,
                merchant=session.merchant,
                description=f'JIT via {jit_bank.upper()} → Kona card at {session.merchant.name}',
            )

        # ── Confirm session ───────────────────────────────────────────────
        session.customer = customer
        session.status = 'confirmed'
        session.confirmed_at = timezone.now()
        session.save()

        # Fire WebSocket to merchant screen
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'session_{session.id}',
            {
                'type': 'payment_confirmed',
                'session_id': str(session.id),
                'amount': str(session.amount),
                'funding_mode': funding_mode,
                'bank_used': data.get('bank', '') or data.get('jit_bank', ''),
                'customer_phone': data['customer_phone'],
            }
        )

        return Response({
            'status': 'confirmed',
            'session_id': str(session.id),
            'amount': str(session.amount),
            'funding_mode': funding_mode,
            'message': 'Payment confirmed successfully.',
        })


# ── Repayments ────────────────────────────────────────────────────────────────

class MakeRepaymentView(APIView):
    def post(self, request):
        serializer = RepaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        customer = get_object_or_404(Customer, phone=data['customer_phone'])

        if customer.statement_balance <= 0 and customer.current_balance <= 0:
            return Response({'error': 'No balance to repay.'}, status=400)

        amount = customer.statement_balance if data['pay_full'] else data['amount']
        amount = Decimal(str(amount))

        # Reduce balances
        customer.current_balance = max(customer.current_balance - amount, Decimal('0'))
        customer.statement_balance = max(customer.statement_balance - amount, Decimal('0'))
        customer.save()

        # Update open statement
        stmt = get_open_statement(customer)
        stmt.total_payments += amount
        stmt.closing_balance = customer.current_balance
        if customer.statement_balance <= 0:
            stmt.status = 'paid_full'
        stmt.save()

        # Record transaction
        CreditTransaction.objects.create(
            customer=customer,
            transaction_type='repayment',
            funding_mode='bank',
            amount=amount,
            statement=stmt,
            description=f'Repayment via {data["bank"].upper()}',
        )

        return Response({
            'status': 'repayment_recorded',
            'amount_paid': str(amount),
            'remaining_balance': str(customer.current_balance),
            'statement_balance': str(customer.statement_balance),
        })


# ── Statements ────────────────────────────────────────────────────────────────

class StatementListView(APIView):
    def get(self, request, phone):
        customer = get_object_or_404(Customer, phone=phone)
        statements = customer.statements.all()
        return Response(CreditStatementSerializer(statements, many=True).data)


class CurrentStatementView(APIView):
    def get(self, request, phone):
        customer = get_object_or_404(Customer, phone=phone)
        stmt = get_open_statement(customer)
        transactions = CreditTransaction.objects.filter(statement=stmt)
        return Response({
            'statement': CreditStatementSerializer(stmt).data,
            'transactions': CreditTransactionSerializer(transactions, many=True).data,
        })


# ── Admin / Dashboard ─────────────────────────────────────────────────────────

class TransactionListView(APIView):
    def get(self, request):
        sessions = PaymentSession.objects.select_related('merchant', 'customer')
        return Response(PaymentSessionSerializer(sessions, many=True).data)


class CreditTransactionListView(APIView):
    def get(self, request):
        txns = CreditTransaction.objects.select_related('customer', 'merchant')
        return Response(CreditTransactionSerializer(txns, many=True).data)


class DashboardStatsView(APIView):
    def get(self, request):
        confirmed = PaymentSession.objects.filter(status='confirmed')
        total_volume = sum(s.amount for s in confirmed)
        customers = Customer.objects.filter(is_active=True)
        total_credit_book = sum(c.current_balance for c in customers)
        total_credit_issued = sum(c.credit_limit for c in customers)
        overdue = [c for c in customers if c.is_overdue]
        overdue_amount = sum(c.statement_balance for c in overdue)

        return Response({
            'total_merchants': Merchant.objects.filter(is_active=True).count(),
            'total_customers': customers.count(),
            'total_transactions': confirmed.count(),
            'total_volume': str(total_volume),
            'total_credit_book': str(total_credit_book),
            'total_credit_issued': str(total_credit_issued),
            'overdue_customers': len(overdue),
            'overdue_amount': str(overdue_amount),
            'credit_utilisation': str(
                round(float(total_credit_book) / float(total_credit_issued) * 100, 1)
                if total_credit_issued > 0 else 0
            ),
        })
