import boto3
import os
import sys
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

# Configuration
REGION = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
BUCKETS = {
    'jhbridge-contracts-prod': {
        'Versioning': True,
        'Encryption': True,
        'CORS': ['GET']  # Pour téléchargement sécurisé via URL signée
    },
    'jhbridge-signatures-prod': {
        'Versioning': True,
        'Encryption': True,
        'CORS': ['GET']
    },
    'jhbridge-documents-prod': {
        'Versioning': False,
        'Encryption': True,
        'CORS': ['GET']
    },
    'jhbridge-temp-uploads': {
        'Versioning': False,
        'Encryption': True,
        'Lifecycle': {'Days': 1},  # Auto-delete après 24h
        'CORS': ['PUT', 'POST']    # Pour upload direct si nécessaire
    },
    'jhbridge-email-assets': {
        'Versioning': False,
        'Encryption': False,       # Public assets
        'CORS': ['GET'],
        'Public': True
    }
}

def get_s3_client():
    try:
        # Correspondance avec les clés du .env (AWS_KEY_ID / AWS_KEY_SECRET)
        aws_access_key_id = os.environ.get('AWS_KEY_ID') or os.environ.get('AWS_ACCESS_KEY_ID')
        aws_secret_access_key = os.environ.get('AWS_KEY_SECRET') or os.environ.get('AWS_SECRET_ACCESS_KEY')
        
        return boto3.client(
            's3',
            region_name=REGION,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )
    except Exception as e:
        print(f"❌ Erreur connexion AWS: {e}")
        return None

def create_bucket(s3, bucket_name, config):
    print(f"\n📦 Traitement du bucket: {bucket_name}")
    
    # 1. Création
    try:
        if REGION == 'us-east-1':
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': REGION}
            )
        print(f"   ✅ Bucket créé (ou existant)")
    except ClientError as e:
        if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
            print(f"   ℹ️  Bucket existe déjà")
        else:
            print(f"   ❌ Erreur création: {e}")
            return

    # 2. Encryption (SSE-S3)
    if config.get('Encryption'):
        try:
            s3.put_bucket_encryption(
                Bucket=bucket_name,
                ServerSideEncryptionConfiguration={
                    'Rules': [{'ApplyServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}}]
                }
            )
            print(f"   🔒 Encryption activée")
        except Exception as e:
            print(f"   ⚠️ Erreur encryption: {e}")

    # 3. Versioning
    if config.get('Versioning'):
        try:
            s3.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            print(f"   📚 Versioning activé")
        except Exception as e:
            print(f"   ⚠️ Erreur versioning: {e}")

    # 4. Lifecycle (pour temp)
    if config.get('Lifecycle'):
        try:
            s3.put_bucket_lifecycle_configuration(
                Bucket=bucket_name,
                LifecycleConfiguration={
                    'Rules': [{
                        'ID': 'AutoDelete',
                        'Status': 'Enabled',
                        'Prefix': '',
                        'Expiration': {'Days': config['Lifecycle']['Days']}
                    }]
                }
            )
            print(f"   ⏱️  Lifecycle configuré ({config['Lifecycle']['Days']} jours)")
        except Exception as e:
            print(f"   ⚠️ Erreur lifecycle: {e}")

    # 5. Public Access Block (Sécurité par défaut)
    if not config.get('Public'):
        try:
            s3.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            )
            print(f"   🛡️  Accès public bloqué")
        except Exception as e:
            print(f"   ⚠️ Erreur blocage public: {e}")
    else:
        # Pour assets publics, on désactive le blocage
        try:
            s3.delete_public_access_block(Bucket=bucket_name)
            
            # Et on ajoute une policy public read
            policy = '''{
                "Version": "2012-10-17",
                "Statement": [{
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": "arn:aws:s3:::%s/*"
                }]
            }''' % bucket_name
            
            s3.put_bucket_policy(Bucket=bucket_name, Policy=policy)
            print(f"   🌍 Accès public activé (Assets)")
        except Exception as e:
            print(f"   ⚠️ Erreur config public: {e}")

    # 6. CORS
    if config.get('CORS'):
        try:
            s3.put_bucket_cors(
                Bucket=bucket_name,
                CORSConfiguration={
                    'CORSRules': [{
                        'AllowedHeaders': ['*'],
                        'AllowedMethods': config['CORS'],
                        'AllowedOrigins': ['*'], # A restreindre en prod
                        'ExposeHeaders': []
                    }]
                }
            )
            print(f"   🌐 CORS configuré")
        except Exception as e:
            print(f"   ⚠️ Erreur CORS: {e}")

if __name__ == "__main__":
    print(f"🚀 Démarrage configuration S3 (Region: {REGION})")
    
    if not os.environ.get('AWS_KEY_ID') and not os.environ.get('AWS_ACCESS_KEY_ID'):
        print("❌ ERREUR: Variables d'environnement AWS manquantes!")
        print("   Définir: AWS_KEY_ID et AWS_KEY_SECRET dans le fichier .env")
        sys.exit(1)

    s3 = get_s3_client()
    if s3:
        for name, cfg in BUCKETS.items():
            create_bucket(s3, name, cfg)
        print("\n✅ Configuration terminée!")
