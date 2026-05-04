from django.urls import path
from . import views

urlpatterns = [
    # Merchants
    path('merchants/', views.MerchantListView.as_view()),
    path('merchants/<uuid:pk>/', views.MerchantDetailView.as_view()),
    path('merchants/<uuid:merchant_id>/latest-session/', views.MerchantLatestSessionView.as_view()),

    # Customers
    path('customers/', views.CustomerListView.as_view()),
    path('customers/<str:phone>/', views.CustomerDetailView.as_view()),

    # Card
    path('card/<str:phone>/', views.CardDetailView.as_view()),
    path('card/freeze/', views.FreezeCardView.as_view()),

    # Statements
    path('statements/<str:phone>/', views.StatementListView.as_view()),
    path('statements/<str:phone>/current/', views.CurrentStatementView.as_view()),

    # Repayments
    path('repayments/', views.MakeRepaymentView.as_view()),

    # Payment Sessions
    path('sessions/create/', views.CreateSessionView.as_view()),
    path('sessions/confirm/', views.ConfirmPaymentView.as_view()),
    path('sessions/<uuid:session_id>/', views.SessionDetailView.as_view()),

    # Admin / Dashboard
    path('transactions/', views.TransactionListView.as_view()),
    path('credit-transactions/', views.CreditTransactionListView.as_view()),
    path('dashboard/stats/', views.DashboardStatsView.as_view()),
]
