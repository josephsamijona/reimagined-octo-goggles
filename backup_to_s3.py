"""
AWS S3 Database Backup Script
Safely backs up Railway MySQL database to AWS S3 with full progress tracking
"""

import os
import sys
import subprocess
import hashlib
import boto3
from datetime import datetime
from pathlib import Path
import logging
from urllib.parse import urlparse
from botocore.exceptions import ClientError
from tqdm import tqdm
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DatabaseBackupToS3:
    """Safe MySQL database backup to AWS S3 with progress tracking"""
    
    def __init__(self):
        """Initialize backup configuration from environment variables"""
        self.backup_dir = Path("C:/backups/mysql")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Parse MySQL URL from Railway
        mysql_url = os.getenv('MYSQL_URL')
        if not mysql_url:
            raise ValueError("MYSQL_URL not found in environment variables")
        
        parsed = urlparse(mysql_url)
        self.db_host = parsed.hostname
        self.db_port = parsed.port or 3306
        self.db_user = parsed.username
        self.db_password = parsed.password
        self.db_name = parsed.path.lstrip('/')
        
        logger.info(f"Database config: {self.db_user}@{self.db_host}:{self.db_port}/{self.db_name}")
        
        # AWS Configuration
        self.aws_access_key = os.getenv('AWS_KEY_ID')
        self.aws_secret_key = os.getenv('AWS_KEY_SECRET')
        
        if not self.aws_access_key or not self.aws_secret_key:
            raise ValueError("AWS credentials not found in environment variables")
        
        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key,
            region_name='us-east-1'  # Default region
        )
        
        # S3 Bucket configuration
        self.bucket_name = 'jhbridge-mysql-backups'
        logger.info(f"AWS S3 bucket: {self.bucket_name}")
    
    def create_s3_bucket(self):
        """Create S3 bucket if it doesn't exist"""
        logger.info(f"[1/6] Checking/Creating S3 bucket: {self.bucket_name}")
        
        try:
            # Check if bucket exists
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"✓ Bucket '{self.bucket_name}' already exists")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code == '404':
                # Bucket doesn't exist, create it
                logger.info(f"Creating new bucket '{self.bucket_name}'...")
                
                try:
                    self.s3_client.create_bucket(
                        Bucket=self.bucket_name,
                        ACL='private'
                    )
                    
                    # Enable versioning for safety
                    self.s3_client.put_bucket_versioning(
                        Bucket=self.bucket_name,
                        VersioningConfiguration={'Status': 'Enabled'}
                    )
                    
                    # Configure lifecycle policy to manage old backups
                    lifecycle_policy = {
                        'Rules': [
                            {
                                'ID': 'DeleteOldBackups',
                                'Status': 'Enabled',
                                'Prefix': 'backups/',
                                'Expiration': {'Days': 30},
                                'NoncurrentVersionExpiration': {'NoncurrentDays': 7}
                            }
                        ]
                    }
                    
                    self.s3_client.put_bucket_lifecycle_configuration(
                        Bucket=self.bucket_name,
                        LifecycleConfiguration=lifecycle_policy
                    )
                    
                    logger.info(f"✓ Bucket '{self.bucket_name}' created successfully")
                    logger.info("✓ Versioning enabled")
                    logger.info("✓ Lifecycle policy configured (30 days retention)")
                    return True
                    
                except ClientError as create_error:
                    logger.error(f"✗ Failed to create bucket: {create_error}")
                    raise
            else:
                logger.error(f"✗ Error accessing bucket: {e}")
                raise
    
    def test_database_connection(self):
        """Test MySQL connection before backup"""
        logger.info("[2/6] Testing database connection...")
        
        try:
            # Test connection with mysql command
            test_cmd = [
                'mysql',
                f'-h{self.db_host}',
                f'-P{self.db_port}',
                f'-u{self.db_user}',
                f'-p{self.db_password}',
                '-e', 'SELECT 1'
            ]
            
            result = subprocess.run(
                test_cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                raise Exception(f"Connection test failed: {result.stderr}")
            
            logger.info(f"✓ Successfully connected to {self.db_host}:{self.db_port}")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("✗ Connection timeout")
            raise
        except FileNotFoundError:
            logger.error("✗ MySQL client not found. Please install MySQL client.")
            raise
        except Exception as e:
            logger.error(f"✗ Connection failed: {e}")
            raise
    
    def create_backup(self):
        """Create MySQL database backup with progress tracking"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = self.backup_dir / f"backup_{timestamp}.sql.gz"
        
        logger.info(f"[3/6] Creating database backup: {backup_file.name}")
        
        # mysqldump command with safe options
        dump_cmd = [
            'mysqldump',
            f'-h{self.db_host}',
            f'-P{self.db_port}',
            f'-u{self.db_user}',
            f'-p{self.db_password}',
            '--databases', self.db_name,
            '--single-transaction',  # Consistent backup without locking
            '--quick',               # Memory efficient
            '--lock-tables=false',   # Don't lock tables (safe for production)
            '--routines',            # Include stored procedures
            '--triggers',            # Include triggers
            '--events',              # Include events
            '--skip-extended-insert', # One row per INSERT (easier to debug)
            '--compress'             # Compress network traffic
        ]
        
        try:
            logger.info("Starting mysqldump...")
            
            # Execute mysqldump with progress tracking
            with open(backup_file, 'wb') as f:
                # Run mysqldump
                dump_process = subprocess.Popen(
                    dump_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # Compress with gzip
                gzip_process = subprocess.Popen(
                    ['gzip'],
                    stdin=dump_process.stdout,
                    stdout=f,
                    stderr=subprocess.PIPE
                )
                
                dump_process.stdout.close()
                
                # Show progress spinner
                with tqdm(desc="Backing up database", unit=" bytes", ncols=100) as pbar:
                    while gzip_process.poll() is None:
                        if backup_file.exists():
                            current_size = backup_file.stat().st_size
                            pbar.n = current_size
                            pbar.refresh()
                        time.sleep(0.5)
                
                # Wait for completion
                gzip_stderr = gzip_process.communicate()[1]
                dump_stderr = dump_process.communicate()[1]
                
                if dump_process.returncode != 0:
                    raise Exception(f"mysqldump failed: {dump_stderr.decode()}")
                
                if gzip_process.returncode != 0:
                    raise Exception(f"gzip failed: {gzip_stderr.decode()}")
            
            file_size = backup_file.stat().st_size
            file_size_mb = file_size / (1024 * 1024)
            
            logger.info(f"✓ Backup created: {file_size_mb:.2f} MB")
            return backup_file
            
        except Exception as e:
            logger.error(f"✗ Backup creation failed: {e}")
            if backup_file.exists():
                backup_file.unlink()
            raise
    
    def calculate_checksum(self, file_path):
        """Calculate SHA256 checksum with progress tracking"""
        logger.info("[4/6] Calculating file checksum...")
        
        sha256_hash = hashlib.sha256()
        file_size = file_path.stat().st_size
        
        with open(file_path, "rb") as f:
            with tqdm(total=file_size, desc="Computing checksum", unit="B", unit_scale=True, ncols=100) as pbar:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
                    pbar.update(len(byte_block))
        
        checksum = sha256_hash.hexdigest()
        logger.info(f"✓ Checksum: {checksum}")
        return checksum
    
    def verify_backup(self, file_path):
        """Verify backup integrity"""
        logger.info("[5/6] Verifying backup integrity...")
        
        try:
            # Test gzip integrity
            result = subprocess.run(
                ['gzip', '-t', str(file_path)],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                raise Exception(f"Backup file is corrupted: {result.stderr}")
            
            logger.info("✓ Backup integrity verified")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("✗ Verification timeout")
            return False
        except Exception as e:
            logger.error(f"✗ Verification failed: {e}")
            return False
    
    def upload_to_s3(self, file_path, checksum):
        """Upload backup to S3 with progress tracking"""
        s3_key = f"backups/{file_path.name}"
        
        logger.info(f"[6/6] Uploading to S3: s3://{self.bucket_name}/{s3_key}")
        
        file_size = file_path.stat().st_size
        
        try:
            # Upload with progress bar
            with tqdm(total=file_size, desc="Uploading to S3", unit="B", unit_scale=True, ncols=100) as pbar:
                def upload_callback(bytes_transferred):
                    pbar.update(bytes_transferred)
                
                self.s3_client.upload_file(
                    str(file_path),
                    self.bucket_name,
                    s3_key,
                    ExtraArgs={
                        'Metadata': {
                            'checksum-sha256': checksum,
                            'backup-date': datetime.now().isoformat(),
                            'database': self.db_name,
                            'source': 'railway'
                        },
                        'StorageClass': 'STANDARD_IA'  # Cheaper for backups
                    },
                    Callback=upload_callback
                )
            
            # Verify upload
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            uploaded_size = response['ContentLength']
            local_size = file_path.stat().st_size
            
            if uploaded_size != local_size:
                raise Exception(f"Upload verification failed: sizes don't match ({local_size} != {uploaded_size})")
            
            logger.info(f"✓ Upload successful: {uploaded_size / (1024*1024):.2f} MB")
            
            # Generate download URL (valid for 7 days)
            download_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=604800  # 7 days
            )
            
            return {
                's3_key': s3_key,
                'size': uploaded_size,
                'download_url': download_url
            }
            
        except Exception as e:
            logger.error(f"✗ Upload failed: {e}")
            raise
    
    def cleanup_old_backups(self, keep_local_days=7):
        """Remove local backups older than specified days"""
        logger.info(f"Cleaning up local backups older than {keep_local_days} days...")
        
        cutoff_time = datetime.now().timestamp() - (keep_local_days * 86400)
        deleted = 0
        
        for backup_file in self.backup_dir.glob("backup_*.sql.gz"):
            if backup_file.stat().st_mtime < cutoff_time:
                backup_file.unlink()
                deleted += 1
                logger.info(f"  Deleted: {backup_file.name}")
        
        logger.info(f"✓ Cleaned up {deleted} old backup(s)")
    
    def run(self):
        """Execute complete backup process with full progress tracking"""
        try:
            logger.info("=" * 80)
            logger.info("RAILWAY MYSQL DATABASE BACKUP TO AWS S3")
            logger.info("=" * 80)
            logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("")
            
            # Step 1: Create/verify S3 bucket
            self.create_s3_bucket()
            
            # Step 2: Test database connection
            self.test_database_connection()
            
            # Step 3: Create backup
            backup_file = self.create_backup()
            
            # Step 4: Calculate checksum
            checksum = self.calculate_checksum(backup_file)
            
            # Step 5: Verify backup
            if not self.verify_backup(backup_file):
                raise Exception("Backup verification failed")
            
            # Step 6: Upload to S3
            upload_info = self.upload_to_s3(backup_file, checksum)
            
            # Cleanup old local backups
            self.cleanup_old_backups(keep_local_days=7)
            
            logger.info("")
            logger.info("=" * 80)
            logger.info("BACKUP COMPLETED SUCCESSFULLY ✓")
            logger.info("=" * 80)
            logger.info(f"Local file: {backup_file}")
            logger.info(f"S3 location: s3://{self.bucket_name}/{upload_info['s3_key']}")
            logger.info(f"File size: {upload_info['size'] / (1024*1024):.2f} MB")
            logger.info(f"Checksum: {checksum}")
            logger.info(f"Download URL (7 days): {upload_info['download_url'][:80]}...")
            logger.info("")
            
            return {
                'success': True,
                'backup_file': str(backup_file),
                's3_bucket': self.bucket_name,
                's3_key': upload_info['s3_key'],
                'size': upload_info['size'],
                'checksum': checksum,
                'download_url': upload_info['download_url']
            }
            
        except Exception as e:
            logger.error("")
            logger.error("=" * 80)
            logger.error(f"BACKUP FAILED: {e}")
            logger.error("=" * 80)
            logger.error("")
            
            # The original database is NEVER touched - only read from
            logger.info("NOTE: Original database remains intact and unchanged.")
            
            return {
                'success': False,
                'error': str(e)
            }


def main():
    """Main entry point"""
    try:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Run backup
        backup = DatabaseBackupToS3()
        result = backup.run()
        
        # Exit with appropriate code
        sys.exit(0 if result['success'] else 1)
        
    except KeyboardInterrupt:
        logger.error("\nBackup interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
