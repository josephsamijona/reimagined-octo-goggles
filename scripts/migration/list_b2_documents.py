import boto3
import os
from dotenv import load_dotenv

load_dotenv()

DOCUMENT_EXTENSIONS = ['.pdf', '.txt', '.doc', '.docx', '.rtf', '.odt']

def get_b2_client():
    return boto3.client(
        's3',
        endpoint_url=os.environ.get('B2_ENDPOINT_URL'),
        aws_access_key_id=os.environ.get('B2_ACCESS_KEY_ID') or os.environ.get('B2_KEY_ID'),
        aws_secret_access_key=os.environ.get('B2_SECRET_ACCESS_KEY') or os.environ.get('B2_APPLICATION_KEY')
    )

def list_documents(bucket_name):
    b2 = get_b2_client()
    print(f"📂 Recherche de documents dans '{bucket_name}'...")
    print(f"   Extensions: {DOCUMENT_EXTENSIONS}\n")
    
    try:
        paginator = b2.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name)
        
        documents = []
        
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key'].lower()
                    if any(key.endswith(ext) for ext in DOCUMENT_EXTENSIONS):
                        documents.append({
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified']
                        })
        
        if documents:
            print(f"{'Fichier':<70} | {'Taille (KB)':>12}")
            print("-" * 85)
            for doc in documents:
                print(f"{doc['key']:<70} | {doc['size']/1024:>12.2f}")
            print("-" * 85)
            print(f"Total Documents: {len(documents)}")
            total_size = sum(d['size'] for d in documents)
            print(f"Total Size: {total_size / (1024*1024):.2f} MB")
        else:
            print("Aucun document trouvé avec ces extensions.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    list_documents('jhbridgestockagesystem')
