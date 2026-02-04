"""
Quick script to analyze backup and database content
"""
import json
import gzip
from app.models import *
from django.apps import apps

# Analyze backup file
print("=" * 80)
print("BACKUP ANALYSIS")
print("=" * 80)

backup_file = 'C:/backups/django/backup_20260203_101906.json.gz'
with gzip.open(backup_file, 'rt') as f:
    data = json.load(f)

print(f"\nTotal objects in backup: {len(data)}")

# Count by model
models_count = {}
for obj in data:
    model = obj['model']
    models_count[model] = models_count.get(model, 0) + 1

print("\nObjects per model in backup:")
for model, count in sorted(models_count.items(), key=lambda x: x[1], reverse=True):
    print(f"  {model}: {count}")

# Compare with actual database
print("\n" + "=" * 80)
print("DATABASE ANALYSIS")
print("=" * 80)

print("\nActual row counts in database:")
print(f"  Users: {User.objects.count()}")
print(f"  Clients: {Client.objects.count()}")
print(f"  Interpreters: {Interpreter.objects.count()}")
print(f"  Assignments: {Assignment.objects.count()}")
print(f"  Languages: {Language.objects.count()}")
print(f"  Quotes: {Quote.objects.count()}")
print(f"  QuoteRequests: {QuoteRequest.objects.count()}")

# Get all app models
print("\nAll Django models:")
for model in apps.get_models():
    if model._meta.app_label == 'app':
        count = model.objects.count()
        print(f"  {model.__name__}: {count}")
