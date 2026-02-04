"""
AWS Lambda Function: B2 to S3 Migration
Exécute la migration directement dans le cloud AWS.

Déploiement:
1. Créer un fichier ZIP avec ce script + boto3
2. Créer une fonction Lambda (Python 3.11, 512MB RAM, 15min timeout)
3. Configurer les variables d'environnement
4. Déclencher manuellement ou via CloudWatch Events
"""
import boto3
import os
import json

# Configuration via Environment Variables
B2_ENDPOINT = os.environ.get('B2_ENDPOINT_URL')
B2_ACCESS_KEY = os.environ.get('B2_ACCESS_KEY_ID')
B2_SECRET_KEY = os.environ.get('B2_SECRET_ACCESS_KEY')
B2_BUCKET = os.environ.get('B2_BUCKET_NAME', 'jhbridgestockagesystem')

S3_BUCKET = os.environ.get('S3_TARGET_BUCKET', 'jhbridge-documents-prod')

# Extensions de documents à migrer
DOCUMENT_EXTENSIONS = ['.pdf', '.txt', '.doc', '.docx']

def get_b2_client():
    return boto3.client(
        's3',
        endpoint_url=B2_ENDPOINT,
        aws_access_key_id=B2_ACCESS_KEY,
        aws_secret_access_key=B2_SECRET_KEY
    )

def get_s3_client():
    # Lambda a déjà les credentials via IAM Role
    return boto3.client('s3')

def lambda_handler(event, context):
    """
    Main Lambda handler.
    Event peut contenir:
    - filter_docs_only: True pour migrer uniquement les documents
    - dry_run: True pour lister sans migrer
    """
    filter_docs = event.get('filter_docs_only', True)
    dry_run = event.get('dry_run', False)
    
    b2 = get_b2_client()
    s3 = get_s3_client()
    
    results = {
        'migrated': [],
        'skipped': [],
        'errors': []
    }
    
    try:
        paginator = b2.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=B2_BUCKET)
        
        for page in pages:
            if 'Contents' not in page:
                continue
                
            for obj in page['Contents']:
                key = obj['Key']
                size = obj['Size']
                
                # Filtrage
                if filter_docs:
                    is_doc = any(key.lower().endswith(ext) for ext in DOCUMENT_EXTENSIONS)
                    
                    # Logic: 
                    # If mode='include_only' (default behavior previously implied by filter_docs_only=True): migrate ONLY docs.
                    # If mode='exclude' (new behavior): migrate everything EXCEPT docs.
                    
                    mode = event.get('filter_mode', 'include') # 'include' or 'exclude'
                    
                    if mode == 'include' and not is_doc:
                        continue
                    if mode == 'exclude' and is_doc:
                        continue
                
                # Vérifier si existe déjà sur S3
                try:
                    s3_head = s3.head_object(Bucket=S3_BUCKET, Key=key)
                    if s3_head['ContentLength'] == size:
                        results['skipped'].append(key)
                        continue
                except s3.exceptions.ClientError:
                    pass  # N'existe pas
                
                if dry_run:
                    results['migrated'].append(f"[DRY-RUN] {key}")
                    continue
                
                # Migration streaming
                try:
                    response = b2.get_object(Bucket=B2_BUCKET, Key=key)
                    s3.upload_fileobj(
                        response['Body'],
                        S3_BUCKET,
                        key,
                        ExtraArgs={
                            'ContentType': response.get('ContentType', 'application/octet-stream')
                        }
                    )
                    results['migrated'].append(key)
                except Exception as e:
                    results['errors'].append({'key': key, 'error': str(e)})
                    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'migrated_count': len(results['migrated']),
            'skipped_count': len(results['skipped']),
            'error_count': len(results['errors']),
            'details': results
        })
    }
