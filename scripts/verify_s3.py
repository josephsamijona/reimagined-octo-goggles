import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from custom_storages import MediaStorage, PublicMediaStorage

def verify_s3():
    print(f"AWS_STORAGE_BUCKET_NAME: {settings.AWS_STORAGE_BUCKET_NAME}")
    print(f"AWS_S3_REGION_NAME: {settings.AWS_S3_REGION_NAME}")
    
    media_storage = MediaStorage()
    public_storage = PublicMediaStorage()
    
    test_path = "profiles/test/image.jpg"
    
    signed_url = media_storage.url(test_path)
    public_url = public_storage.url(test_path)
    
    print("\nGenerated URLs:")
    print(f"Signed URL (expires): {signed_url}")
    print(f"Public URL (no query): {public_url}")
    
    if 'X-Amz-Algorithm=' in signed_url:
        print("\nSUCCESS: MediaStorage is generating signed URLs.")
    else:
        print("\nWARNING: MediaStorage is NOT generating signed URLs. Check AWS_QUERYSTRING_AUTH.")
        
    if 'X-Amz-Algorithm=' not in public_url:
        print("SUCCESS: PublicMediaStorage is generating public (unsigned) URLs.")
    else:
        print("WARNING: PublicMediaStorage is generating signed URLs. Check querystring_auth.")

if __name__ == "__main__":
    verify_s3()
