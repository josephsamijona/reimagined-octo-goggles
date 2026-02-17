import os
import json
import gzip
import boto3
import subprocess
import logging
from datetime import datetime
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')
secrets_client = boto3.client('secretsmanager')

def get_secret(secret_name):
    """Retrieve database credentials from AWS Secrets Manager"""
    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        if 'SecretString' in response:
            return json.loads(response['SecretString'])
        else:
            raise Exception("Secret binary not supported")
    except ClientError as e:
        logger.error(f"Failed to retrieve secret {secret_name}: {e}")
        raise

def lambda_handler(event, context):
    """
    AWS Lambda Handler for Database Backup
    Triggers: EventBridge Schedule (Cron)
    """
    logger.info("Starting database backup process")
    
    # 1. Configuration
    secret_name = os.environ.get('SECRET_NAME')
    bucket_name = os.environ.get('BACKUP_BUCKET_NAME')
    
    if not secret_name or not bucket_name:
        logger.error("Missing environment variables: SECRET_NAME or BACKUP_BUCKET_NAME")
        return {
            'statusCode': 500,
            'body': json.dumps('Configuration Error: Missing environment variables')
        }

    # 2. Get Credentials
    try:
        creds = get_secret(secret_name)
        db_host = creds.get('host')
        db_port = str(creds.get('port', 3306))
        db_user = creds.get('username')
        db_password = creds.get('password')
        db_name = creds.get('dbname') # Optional: if missing, could dump all databases
        
        if not all([db_host, db_user, db_password]):
             raise Exception("Incomplete database credentials in Secret")
             
    except Exception as e:
        logger.error(f"Credential retrieval failed: {e}")
        return {'statusCode': 500, 'body': json.dumps(f'Credential Error: {str(e)}')}

    # 3. Prepare Backup Paths
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"backup_{db_name or 'all'}_{timestamp}.sql.gz"
    local_path = f"/tmp/{filename}"
    s3_key = f"backups/{filename}"
    
    logger.info(f"Target backup file: {local_path}")

    # 4. Execute mysqldump -> gzip -> file
    # Using simple file redirection is safest for limiting memory usage (stream to disk)
    # Ensure Lambda Ephemeral Storage is configured to be large enough (e.g. 5GB)
    
    dump_cmd = [
        'mysqldump',
        f'--host={db_host}',
        f'--port={db_port}',
        f'--user={db_user}',
        f'--password={db_password}',
        '--single-transaction',
        '--quick',
        '--compress',
        '--set-gtid-purged=OFF',
        '--column-statistics=0' # Fix for version mismatch errors sometimes
    ]
    
    if db_name:
        dump_cmd.append(db_name)
    else:
        dump_cmd.append('--all-databases')

    try:
        logger.info("Starting mysqldump...")
        
        with open(local_path, 'wb') as f_out:
            # Popen mysqldump
            p1 = subprocess.Popen(dump_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Popen gzip
            p2 = subprocess.Popen(['gzip'], stdin=p1.stdout, stdout=f_out, stderr=subprocess.PIPE)
            
            # Allow p1 to receive a SIGPIPE if p2 exits
            p1.stdout.close() 
            
            # Wait for completion
            stderr_gzip = p2.communicate()[1]
            stderr_dump = p1.communicate()[1]
            
            if p1.returncode != 0:
                logger.error(f"mysqldump error: {stderr_dump.decode()}")
                raise Exception(f"mysqldump failed: {stderr_dump.decode()}")
            
            if p2.returncode != 0:
                logger.error(f"gzip error: {stderr_gzip.decode()}")
                raise Exception(f"gzip failed: {stderr_gzip.decode()}")
                
        file_size = os.path.getsize(local_path)
        logger.info(f"Backup created successfully: {file_size / (1024*1024):.2f} MB")

    except Exception as e:
        logger.error(f"Backup creation failed: {e}")
        # Clean up if exists
        if os.path.exists(local_path):
            os.remove(local_path)
        return {'statusCode': 500, 'body': json.dumps(f'Backup Error: {str(e)}')}

    # 5. Upload to S3
    try:
        logger.info(f"Uploading to S3 bucket: {bucket_name}, key: {s3_key}")
        s3_client.upload_file(
            local_path, 
            bucket_name, 
            s3_key,
            ExtraArgs={'StorageClass': 'STANDARD_IA'} # Save cost
        )
        logger.info("Upload complete")
        
    except Exception as e:
        logger.error(f"S3 Upload failed: {e}")
        if os.path.exists(local_path):
            os.remove(local_path)
        return {'statusCode': 500, 'body': json.dumps(f'Upload Error: {str(e)}')}

    # 6. Cleanup
    if os.path.exists(local_path):
        os.remove(local_path)
        logger.info("Local temporary file cleaned up")

    return {
        'statusCode': 200,
        'body': json.dumps(f"Backup successful: s3://{bucket_name}/{s3_key}")
    }
