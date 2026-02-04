import boto3
import os
import sys
from dotenv import load_dotenv

# Config
load_dotenv()

def get_b2_client():
    return boto3.client(
        's3',
        endpoint_url=os.environ.get('B2_ENDPOINT_URL'),
        aws_access_key_id=os.environ.get('B2_ACCESS_KEY_ID') or os.environ.get('B2_KEY_ID'),
        aws_secret_access_key=os.environ.get('B2_SECRET_ACCESS_KEY') or os.environ.get('B2_APPLICATION_KEY')
    )

def list_buckets():
    b2 = get_b2_client()
    try:
        response = b2.list_buckets()
        print("\n📦 Backblaze B2 Buckets:")
        if 'Buckets' in response:
            for bucket in response['Buckets']:
                print(f"   - {bucket['Name']} (Created: {bucket['CreationDate']})")
        else:
            print("   No buckets found.")
            
    except Exception as e:
        print(f"❌ Error listing buckets: {e}")

if __name__ == "__main__":
    list_buckets()
