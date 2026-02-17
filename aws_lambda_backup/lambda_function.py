import os
import json
import gzip
import boto3
import subprocess
import logging
import resend
from datetime import datetime
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')
secrets_client = boto3.client('secretsmanager')

# Email Configuration
CEO_EMAIL = "jhbridgetranslation@gmail.com"
CTO_EMAILS = ["isteah.josephsamuel@gmail.com", "josephsamueljonathan@gmail.com"]
RECIPIENTS = [CEO_EMAIL] + CTO_EMAILS

def send_notification(subject, body, is_error=False):
    """Send email notification via Resend"""
    api_key = os.environ.get('RESEND_API_KEY')
    if not api_key:
        logger.error("RESEND_API_KEY missing. Cannot send email.")
        return

    resend.api_key = api_key
    
    try:
        # Send to all recipients
        # Resend supports multiple 'to' addresses
        r = resend.Emails.send({
            "from": "AWS Backup <backup@resend.dev>", # or a verified domain if available
            "to": RECIPIENTS,
            "subject": subject,
            "html": body
        })
        logger.info(f"Email sent: {r}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")

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
        msg = "Missing environment variables: SECRET_NAME or BACKUP_BUCKET_NAME"
        logger.error(msg)
        send_notification("Backup Configuration Error", f"<p>Error: {msg}</p>", is_error=True)
        return {
            'statusCode': 500,
            'body': json.dumps(msg)
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
        msg = f"Credential retrieval failed: {e}"
        logger.error(msg)
        send_notification("Backup Credential Error", f"<p>{msg}</p>", is_error=True)
        return {'statusCode': 500, 'body': json.dumps(msg)}

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
        file_size_mb = file_size / (1024*1024)
        logger.info(f"Backup created successfully: {file_size_mb:.2f} MB")

    except Exception as e:
        msg = f"Backup creation failed: {e}"
        logger.error(msg)
        # Clean up if exists
        if os.path.exists(local_path):
            os.remove(local_path)
        send_notification("Backup Creation Failed", f"<p>The backup process failed during dump/compression.</p><p>Error: {str(e)}</p>", is_error=True)
        return {'statusCode': 500, 'body': json.dumps(msg)}

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
        
        # Success Notification
        email_body = f"""
        <h1>Database Backup Successful</h1>
        <p><strong>Bonjour,</strong></p>
        <p>Le backup de la base de données a été effectué avec succès.</p>
        <ul>
            <li><strong>Date:</strong> {timestamp}</li>
            <li><strong>Fichier:</strong> {filename}</li>
            <li><strong>Taille:</strong> {file_size_mb:.2f} MB</li>
            <li><strong>Bucket:</strong> {bucket_name}</li>
        </ul>
        <p>Cordialement,<br>AWS Lambda Backup Service</p>
        """
        send_notification(f"Backup Success: {filename}", email_body)
        
    except Exception as e:
        msg = f"S3 Upload failed: {e}"
        logger.error(msg)
        send_notification("Backup Upload Failed", f"<p>Backup was created but failed to upload to S3.</p><p>Error: {str(e)}</p>", is_error=True)
        
        if os.path.exists(local_path):
            os.remove(local_path)
        return {'statusCode': 500, 'body': json.dumps(msg)}

    # 6. Cleanup
    if os.path.exists(local_path):
        os.remove(local_path)
        logger.info("Local temporary file cleaned up")

    return {
        'statusCode': 200,
        'body': json.dumps(f"Backup successful: s3://{bucket_name}/{s3_key}")
    }
