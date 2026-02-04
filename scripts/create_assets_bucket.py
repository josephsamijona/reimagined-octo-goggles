import boto3
import os
import sys
from dotenv import load_dotenv

load_dotenv()

REGION = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
BUCKET_NAME = 'jhbridge-assets'

def create_assets_bucket():
    aws_access_key_id = os.environ.get('AWS_KEY_ID') or os.environ.get('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.environ.get('AWS_KEY_SECRET') or os.environ.get('AWS_SECRET_ACCESS_KEY')
    
    s3 = boto3.client(
        's3',
        region_name=REGION,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key
    )
    
    print(f"📦 Creating bucket: {BUCKET_NAME}")
    try:
        if REGION == 'us-east-1':
            s3.create_bucket(Bucket=BUCKET_NAME)
        else:
            s3.create_bucket(
                Bucket=BUCKET_NAME,
                CreateBucketConfiguration={'LocationConstraint': REGION}
            )
        print("   ✅ Created successfully")
        
        # Configure CORS for assets (public/web access usually needed)
        s3.put_bucket_cors(
            Bucket=BUCKET_NAME,
            CORSConfiguration={
                'CORSRules': [{
                    'AllowedHeaders': ['*'],
                    'AllowedMethods': ['GET'],
                    'AllowedOrigins': ['*'],
                    'ExposeHeaders': []
                }]
            }
        )
        print("   🌐 CORS Configured")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    create_assets_bucket()
