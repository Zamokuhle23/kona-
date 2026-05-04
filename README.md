# Kona App — Backend

Django + Django REST Framework + Django Channels

## Setup (Windows)

### 1. Create and activate virtual environment
```cmd
python -m venv venv
venv\Scripts\activate
```

### 2. Install dependencies
```cmd
pip install -r requirements.txt
```

### 3. Create Django project scaffold
```cmd
django-admin startproject config_temp .
```
Then DELETE the auto-generated config folder — the one provided here already has the correct settings.

### 4. Run migrations
```cmd
python manage.py makemigrations payments
python manage.py migrate
```

### 5. Create superuser (for admin panel)
```cmd
python manage.py createsuperuser
```
Suggested: username=admin, password=admin123

### 6. Load test data
```cmd
python seed.py
```

### 7. Start server
```cmd
python manage.py runserver
```

## Test URLs
- Admin panel:       http://127.0.0.1:8000/admin/
- Merchants:         http://127.0.0.1:8000/api/merchants/
- Customers:         http://127.0.0.1:8000/api/customers/
- Dashboard stats:   http://127.0.0.1:8000/api/dashboard/stats/
- Transactions:      http://127.0.0.1:8000/api/transactions/
- BNPL Loans:        http://127.0.0.1:8000/api/loans/

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | /api/merchants/ | List all merchants |
| POST | /api/merchants/ | Create merchant |
| GET | /api/customers/ | List all customers |
| POST | /api/customers/ | Create customer |
| GET | /api/customers/{phone}/ | Get customer by phone |
| POST | /api/sessions/create/ | Merchant creates payment session |
| GET | /api/sessions/{id}/ | Customer fetches session (amount, merchant) |
| POST | /api/sessions/confirm/ | Customer confirms payment |
| GET | /api/transactions/ | All transactions (admin) |
| GET | /api/loans/ | All BNPL loans (admin) |
| GET | /api/dashboard/stats/ | Summary stats |

## WebSocket
Connect to: ws://127.0.0.1:8000/ws/session/{session_id}/
Fires 'payment_confirmed' event when customer pays.
