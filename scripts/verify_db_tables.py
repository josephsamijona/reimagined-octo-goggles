import os
import sys
import django
from django.db import connection

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

def check_tables():
    with connection.cursor() as cursor:
        # Get all table names
        table_names = connection.introspection.table_names(cursor)
        
        target_tables = ['app_contract_invitation', 'app_contract_tracking_event']
        missing_tables = [t for t in target_tables if t not in table_names]
        
        if missing_tables:
            print(f"MISSING TABLES: {missing_tables}")
            return
        
        print("ALL TABLES FOUND.")
        
        # Check columns for contract_invitation
        print("\nChecking app_contract_invitation columns:")
        columns = [col.name for col in connection.introspection.get_table_description(cursor, 'app_contract_invitation')]
        expected_cols = ['id', 'invitation_number', 'interpreter_id', 'contract_signature_id', 'status', 'token', 'accept_token', 'review_token', 'pdf_s3_key']
        for col in expected_cols:
            if col in columns:
                print(f"  [OK] {col}")
            else:
                print(f"  [MISSING] {col}")

        # Check columns for contract_tracking_event
        print("\nChecking app_contract_tracking_event columns:")
        columns = [col.name for col in connection.introspection.get_table_description(cursor, 'app_contract_tracking_event')]
        expected_cols = ['id', 'invitation_id', 'event_type', 'timestamp', 'metadata']
        for col in expected_cols:
            if col in columns:
                print(f"  [OK] {col}")
            else:
                print(f"  [MISSING] {col}")

if __name__ == "__main__":
    check_tables()
