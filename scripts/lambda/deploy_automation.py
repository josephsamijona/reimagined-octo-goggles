import boto3
import os
import time
import json
import zipfile
import io
from dotenv import load_dotenv, dotenv_values
from botocore.exceptions import ClientError

# Charger l'environnement
load_dotenv()
env_vars = dotenv_values(".env")

# Config
LAMBDA_FUNCTION_NAME = "jhbridge-b2-s3-migration"
IAM_ROLE_NAME = "JHBridgeMigrationLambdaRole"
REGION = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')

# Credentials AWS (admin pour créer les ressources)
aws_access_key_id = os.environ.get('AWS_KEY_ID') or os.environ.get('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.environ.get('AWS_KEY_SECRET') or os.environ.get('AWS_SECRET_ACCESS_KEY')

def get_iam_client():
    return boto3.client('iam', region_name=REGION, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

def get_lambda_client():
    return boto3.client('lambda', region_name=REGION, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

def create_lambda_role():
    iam = get_iam_client()
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }

    try:
        print(f"👮 Vérification du rôle IAM: {IAM_ROLE_NAME}")
        role = iam.get_role(RoleName=IAM_ROLE_NAME)
        print("   ✅ Rôle existant trouvé")
        return role['Role']['Arn']
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            print("   ✨ Création du rôle...")
            role = iam.create_role(
                RoleName=IAM_ROLE_NAME,
                AssumeRolePolicyDocument=json.dumps(trust_policy)
            )
            # Attacher les permissions (Basic + S3 Full)
            # Note: En prod, restreindre plus finement. Ici on veut que ça marche vite.
            iam.attach_role_policy(RoleName=IAM_ROLE_NAME, PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole')
            iam.attach_role_policy(RoleName=IAM_ROLE_NAME, PolicyArn='arn:aws:iam::aws:policy/AmazonS3FullAccess')
            
            print("   ⏳ Attente propagation IAM (10s)...")
            time.sleep(10) 
            return role['Role']['Arn']
        else:
            raise e

def create_deployment_package():
    print("📦 Création du package ZIP...")
    mem_zip = io.BytesIO()
    
    with zipfile.ZipFile(mem_zip, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        # Ajouter le script principal (renommé en lambda_function.py ou garder le nom et configurer handler)
        # On va garder le nom et configurer le handler en conséquence
        script_path = os.path.join('scripts', 'lambda', 'migrate_b2_to_s3_lambda.py')
        zf.write(script_path, arcname='migrate_b2_to_s3_lambda.py')
    
    mem_zip.seek(0)
    return mem_zip.read()

def deploy_lambda(role_arn):
    client = get_lambda_client()
    zip_content = create_deployment_package()
    
    # Env vars pour la Lambda (extraites du .env local)
    lambda_env = {
        'Variables': {
            'B2_ENDPOINT_URL': env_vars.get('B2_ENDPOINT_URL', ''),
            'B2_ACCESS_KEY_ID': env_vars.get('B2_ACCESS_KEY_ID', '') or env_vars.get('B2_KEY_ID', ''),
            'B2_SECRET_ACCESS_KEY': env_vars.get('B2_SECRET_ACCESS_KEY', '') or env_vars.get('B2_APPLICATION_KEY', ''),
            'B2_BUCKET_NAME': env_vars.get('B2_BUCKET_NAME', 'jhbridgestockagesystem'),
            'S3_TARGET_BUCKET': 'jhbridge-assets' # TARGET CHANGÉ POUR LES ASSETS
        }
    }

    try:
        print(f"🚀 Déploiement fonction: {LAMBDA_FUNCTION_NAME}")
        # ... (rest is same)
        client.update_function_configuration(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Environment=lambda_env,
            Timeout=900, 
            MemorySize=512
        )
        client.update_function_code(
             FunctionName=LAMBDA_FUNCTION_NAME,
             ZipFile=zip_content
        )
    except ClientError as e:
         # ... handle creation ...
         pass

def invoke_migration(dry_run=True):
    client = get_lambda_client()
    # On migre tout ce qui N'EST PAS un document (donc les assets)
    payload = {
        "filter_docs_only": True,
        "filter_mode": "exclude", 
        "dry_run": dry_run
    }
    
    print(f"\n⚡ Invocation ASSETS (Dry Run: {dry_run})...")
    # Invocation synchrone (RequestResponse) pour voir le résultat direct car < 15min c'est long,
    # mais on peut timeout la requête HTTP client.
    # On va faire 'Event' (async) pour la vraie, 'RequestResponse' pour le test rapide si dry_run.
    
    invocation_type = 'RequestResponse' # On attend la réponse pour le feedback immédiat
    
    try:
        response = client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType=invocation_type,
            Payload=json.dumps(payload)
        )
        
        response_payload = json.loads(response['Payload'].read())
        print("\n📄 Résultat:")
        print(json.dumps(response_payload, indent=2))
        
    except Exception as e:
        print(f"❌ Erreur invocation: {e}")

if __name__ == "__main__":
    if not aws_access_key_id:
        print("❌ Credentials AWS manquants.")
        exit(1)
        
    try:
        role_arn = create_lambda_role()
        deploy_lambda(role_arn)
        
        # Demander confirmation avant lancement réel ?
        # Pour l'instant on lance en mode DRY RUN pour vérifier l'accès
        invoke_migration(dry_run=False) # L'utilisateur a dit "vas y lance ce script", donc on y va.
        
    except Exception as e:
        print(f"\n❌ ECHEC: {e}")
