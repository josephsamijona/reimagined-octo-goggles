import boto3
import os
from dotenv import load_dotenv

load_dotenv()

def get_b2_client():
    return boto3.client(
        's3',
        endpoint_url=os.environ.get('B2_ENDPOINT_URL'),
        aws_access_key_id=os.environ.get('B2_ACCESS_KEY_ID') or os.environ.get('B2_KEY_ID'),
        aws_secret_access_key=os.environ.get('B2_SECRET_ACCESS_KEY') or os.environ.get('B2_APPLICATION_KEY')
    )

def list_contents(bucket_name):
    b2 = get_b2_client()
    print(f"📂 Listing contents of bucket: '{bucket_name}'...")
    
    try:
        paginator = b2.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name)
        
        file_count = 0
        total_size = 0
        
        print(f"\n{'Key':<60} | {'Size (KB)':>10}")
        print("-" * 75)
        
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    size = obj['Size']
                    file_count += 1
                    total_size += size
                    print(f"{key:<60} | {size/1024:>10.2f}")
            else:
                print("   (Bucket is empty or no contents returned)")
                
        print("-" * 75)
        print(f"Total Files: {file_count}")
        print(f"Total Size:  {total_size / (1024*1024):.2f} MB")

    except Exception as e:
        print(f"❌ Error listing contents: {e}")

if __name__ == "__main__":
    bucket = 'jhbridgestockagesystem'
    list_contents(bucket)
