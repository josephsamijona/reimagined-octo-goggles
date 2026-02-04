import boto3
import os
from dotenv import load_dotenv

load_dotenv()

TARGET_BUCKET = 'jhbridge-assets'

def get_s3_client():
    return boto3.client(
        's3',
        region_name=os.environ.get('AWS_S3_REGION_NAME', 'us-east-1'),
        aws_access_key_id=os.environ.get('AWS_KEY_ID') or os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_KEY_SECRET') or os.environ.get('AWS_SECRET_ACCESS_KEY')
    )

def list_s3_contents():
    s3 = get_s3_client()
    print(f"📦 Listing S3 Bucket: {TARGET_BUCKET}")
    
    try:
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=TARGET_BUCKET)
        
        count = 0
        total_size = 0
        
        print(f"\n{'Key':<60} | {'Size (KB)':>10}")
        print("-" * 75)
        
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    print(f"{obj['Key']:<60} | {obj['Size']/1024:>10.2f}")
                    count += 1
                    total_size += obj['Size']
            else:
                print("   (Empty bucket)")
                
        print("-" * 75)
        print(f"Total Files: {count}")
        print(f"Total Size:  {total_size / (1024*1024):.2f} MB")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    list_s3_contents()
