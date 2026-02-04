import boto3
import os
import sys
import time
from dotenv import load_dotenv
from botocore.exceptions import ClientError
from boto3.s3.transfer import TransferConfig

# Config
load_dotenv()

# Mapping des préfixes B2 vers Buckets S3
BUCKET_MAPPING = {
    'signatures/': 'jhbridge-signatures-prod',
    'interpreter_contracts/': 'jhbridge-contracts-prod',
    'contracts/': 'jhbridge-contracts-prod',
    'documents/': 'jhbridge-documents-prod',
    'payment_proofs/': 'jhbridge-documents-prod',
    'interpreter_payment_proofs/': 'jhbridge-documents-prod',
    'receipts/': 'jhbridge-documents-prod',
    'company_logos/': 'jhbridge-email-assets',
    'interpreter_profiles/': 'jhbridge-documents-prod',
    # Default fallback
    'DEFAULT': 'jhbridge-documents-prod'
}

def get_b2_client():
    return boto3.client(
        's3',
        endpoint_url=os.environ.get('B2_ENDPOINT_URL'),
        aws_access_key_id=os.environ.get('B2_ACCESS_KEY_ID') or os.environ.get('B2_KEY_ID'),
        aws_secret_access_key=os.environ.get('B2_SECRET_ACCESS_KEY') or os.environ.get('B2_APPLICATION_KEY')
    )

def get_s3_client():
    return boto3.client(
        's3',
        region_name=os.environ.get('AWS_S3_REGION_NAME', 'us-east-1'),
        aws_access_key_id=os.environ.get('AWS_KEY_ID') or os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_KEY_SECRET') or os.environ.get('AWS_SECRET_ACCESS_KEY')
    )

def determine_target_bucket(key):
    for prefix, bucket in BUCKET_MAPPING.items():
        if prefix != 'DEFAULT' and key.startswith(prefix):
            return bucket
    return BUCKET_MAPPING['DEFAULT']

def migrate_files():
    b2 = get_b2_client()
    s3 = get_s3_client()
    source_bucket = os.environ.get('B2_BUCKET_NAME')
    
    if not source_bucket:
        print("❌ ERREUR: B2_BUCKET_NAME non défini dans .env")
        return

    print(f"🚀 Démarrage migration: B2 ({source_bucket}) -> AWS S3")
    print(f"   Mapping: {BUCKET_MAPPING}")

    paginator = b2.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=source_bucket)

    total_files = 0
    success_count = 0
    error_count = 0
    skipped_count = 0

    for page in pages:
        if 'Contents' not in page:
            continue
            
        for obj in page['Contents']:
            total_files += 1
            key = obj['Key']
            size = obj['Size']
            target_bucket = determine_target_bucket(key)
            
            print(f"\n📄 Traitement: {key} ({size/1024:.2f} KB)")
            print(f"   ➜ Destination: {target_bucket}")

            # Vérifier si fichier existe déjà sur S3 (Check d'intégrité simple)
            try:
                s3_obj = s3.head_object(Bucket=target_bucket, Key=key)
                if s3_obj['ContentLength'] == size:
                    print("   ⏭️  Existe déjà (taille identique) - SKIPPED")
                    skipped_count += 1
                    continue
            except ClientError:
                pass # N'existe pas, on continue

            # Téléchargement & Upload (Streaming)
            try:
                # On utilise get_object body comme stream pour upload
                response = b2.get_object(Bucket=source_bucket, Key=key)
                s3.upload_fileobj(
                    response['Body'],
                    target_bucket,
                    key,
                    ExtraArgs={'ContentType': response.get('ContentType', 'application/octet-stream')}
                )
                print("   ✅ Migré avec succès")
                success_count += 1
            except Exception as e:
                print(f"   ❌ Erreur migration: {e}")
                error_count += 1

    print("\n" + "="*50)
    print(f"🏁 Migration Terminée")
    print(f"   Total fichiers scannés: {total_files}")
    print(f"   ✅ Succès: {success_count}")
    print(f"   ⏭️  Skipped (Existants): {skipped_count}")
    print(f"   ❌ Erreurs: {error_count}")
    print("="*50)

if __name__ == "__main__":
    if '--help' in sys.argv:
        print("Usage: python scripts/migration/migrate_b2_to_s3.py")
        sys.exit(0)
    
    try:
        migrate_files()
    except KeyboardInterrupt:
        print("\n⚠️ Migration interrompue par l'utilisateur.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur critique: {e}")
        sys.exit(1)
