"""
Run this once after migrations to populate test data:
  python seed.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from payments.models import Merchant, Customer

# Clear existing
Merchant.objects.all().delete()
Customer.objects.all().delete()

# Test merchants
merchants = [
    {'name': 'Nhlangano Furniture', 'business_type': 'Furniture', 'phone': '+26876100001', 'location': 'Nhlangano'},
    {'name': 'Manzini Hardware', 'business_type': 'Hardware', 'phone': '+26876100002', 'location': 'Manzini'},
    {'name': 'Mbabane Pharmacy', 'business_type': 'Pharmacy', 'phone': '+26876100003', 'location': 'Mbabane'},
    {'name': 'Siteki Clothing', 'business_type': 'Clothing', 'phone': '+26876100004', 'location': 'Siteki'},
    {'name': 'Pigg\'s Peak Agri', 'business_type': 'Agriculture', 'phone': '+26876100005', 'location': 'Pigg\'s Peak'},
]

for m in merchants:
    Merchant.objects.create(**m)

# Test customers
customers = [
    {'phone': '+26876200001', 'full_name': 'Sipho Dlamini', 'bank': 'fnb', 'bnpl_limit': 3000},
    {'phone': '+26876200002', 'full_name': 'Nomvula Nkosi', 'bank': 'standard', 'bnpl_limit': 2000},
    {'phone': '+26876200003', 'full_name': 'Bongani Simelane', 'bank': 'nedbank', 'bnpl_limit': 1500},
    {'phone': '+26876200004', 'full_name': 'Thandi Masuku', 'bank': 'eswatini_bank', 'bnpl_limit': 2500},
]

for c in customers:
    Customer.objects.create(**c)

print(f"✓ Created {len(merchants)} merchants")
print(f"✓ Created {len(customers)} customers")
print("\nMerchant IDs (copy one for testing):")
for m in Merchant.objects.all():
    print(f"  {m.name}: {m.id}")
