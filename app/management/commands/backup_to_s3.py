"""
Django Management Command: Backup Database to AWS S3
Safely exports Django database to AWS S3 using dumpdata (no mysqldump required)
"""

import os
import gzip
import hashlib
import logging
import time
from datetime import datetime
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.conf import settings
from tqdm import tqdm


class Command(BaseCommand):
    help = 'Backup Django database to AWS S3 (no mysqldump required)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--exclude-apps',
            nargs='+',
            default=['contenttypes', 'sessions'],
            help='Apps to exclude from backup (default: contenttypes, sessions)'
        )
        parser.add_argument(
            '--bucket',
            type=str,
            default='jhbridge-mysql-backups',
            help='S3 bucket name (default: jhbridge-mysql-backups)'
        )
        parser.add_argument(
            '--keep-local',
            type=int,
            default=7,
            help='Days to keep local backups (default: 7)'
        )

    def _setup_logging(self):
        """Configure logging to both file and console"""
        log_file = Path("backup.log")
        
        # Create logger
        self.logger = logging.getLogger("django.backup")
        self.logger.setLevel(logging.INFO)
        
        # Prevent duplicate handlers
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        # Formatters
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # File Handler
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setFormatter(file_formatter)
        self.logger.addHandler(fh)

        # Success/Error style helper
        self.STYLE_SUCCESS = self.style.SUCCESS
        self.STYLE_WARNING = self.style.WARNING
        self.STYLE_ERROR = self.style.ERROR

    def log(self, message, level="info", style=None):
        """Helper to log to file and write to stdout with Django styling"""
        if level == "info":
            self.logger.info(message)
            out_msg = style(message) if style else message
            self.stdout.write(out_msg)
        elif level == "error":
            self.logger.error(message)
            self.stdout.write(self.style.ERROR(message))
        elif level == "warning":
            self.logger.warning(message)
            self.stdout.write(self.style.WARNING(message))

    def handle(self, *args, **options):
        self._setup_logging()
        
        start_time_total = time.perf_counter()
        
        self.stdout.write("=" * 80)
        self.log("DJANGO DATABASE BACKUP TO AWS S3", style=self.STYLE_SUCCESS)
        self.stdout.write("=" * 80)
        self.log(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        try:
            # Initialize
            self.bucket_name = options['bucket']
            self.exclude_apps = options['exclude_apps']
            self.keep_local_days = options['keep_local']
            
            # Setup directories
            self.backup_dir = Path("C:/backups/django")
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize S3
            self.s3_client = self._init_s3_client()
            
            # 1. Bucket Check
            step_start = time.perf_counter()
            self._create_s3_bucket()
            self.log(f"   [Step Duration: {time.perf_counter() - step_start:.2f}s]")
            
            # 2. Database Export
            step_start = time.perf_counter()
            backup_file = self._export_database()
            self.log(f"   [Step Duration: {time.perf_counter() - step_start:.2f}s]")
            
            # 3. Checksum
            step_start = time.perf_counter()
            checksum = self._calculate_checksum(backup_file)
            self.log(f"   [Step Duration: {time.perf_counter() - step_start:.2f}s]")
            
            # 4. Integrity
            step_start = time.perf_counter()
            self._verify_backup(backup_file)
            self.log(f"   [Step Duration: {time.perf_counter() - step_start:.2f}s]")
            
            # 5. S3 Upload
            step_start = time.perf_counter()
            upload_info = self._upload_to_s3(backup_file, checksum)
            self.log(f"   [Step Duration: {time.perf_counter() - step_start:.2f}s]")
            
            # 6. Cleanup
            step_start = time.perf_counter()
            self._cleanup_old_backups()
            self.log(f"   [Step Duration: {time.perf_counter() - step_start:.2f}s]")
            
            # Success summary
            total_duration = time.perf_counter() - start_time_total
            self.stdout.write("\n" + "=" * 80)
            self.log("[OK] BACKUP COMPLETED SUCCESSFULLY", style=self.STYLE_SUCCESS)
            self.stdout.write("=" * 80)
            self.log(f"Total time: {total_duration:.2f} seconds")
            self.log(f"Local file: {backup_file}")
            self.log(f"S3 location: s3://{self.bucket_name}/{upload_info['s3_key']}")
            self.log(f"File size: {upload_info['size'] / (1024*1024):.2f} MB")
            self.log(f"Checksum: {checksum}")
            
        except Exception as e:
            self.stdout.write("\n" + "=" * 80)
            self.log(f"BACKUP FAILED: {e}", level="error")
            self.stdout.write("=" * 80)
            raise CommandError(f"Backup failed: {e}")

    def _init_s3_client(self):
        """Initialize AWS S3 client from environment variables"""
        aws_access_key = os.getenv('AWS_KEY_ID')
        aws_secret_key = os.getenv('AWS_KEY_SECRET')
        
        if not aws_access_key or not aws_secret_key:
            raise CommandError("AWS credentials not found in environment variables")
        
        return boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name='us-east-1'
        )

    def _create_s3_bucket(self):
        """Create S3 bucket if it doesn't exist"""
        self.log(f"[1/6] Checking S3 bucket: {self.bucket_name}")
        
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            self.log(f"   [OK] Bucket exists", style=self.STYLE_SUCCESS)
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                self.log(f"   Bucket '{self.bucket_name}' not found. Creating...")
                
                self.s3_client.create_bucket(
                    Bucket=self.bucket_name,
                    ACL='private'
                )
                
                # Enable versioning
                self.s3_client.put_bucket_versioning(
                    Bucket=self.bucket_name,
                    VersioningConfiguration={'Status': 'Enabled'}
                )
                
                # Lifecycle policy
                self.s3_client.put_bucket_lifecycle_configuration(
                    Bucket=self.bucket_name,
                    LifecycleConfiguration={
                        'Rules': [{
                            'ID': 'DeleteOldBackups',
                            'Status': 'Enabled',
                            'Prefix': 'backups/',
                            'Expiration': {'Days': 30},
                            'NoncurrentVersionExpiration': {'NoncurrentDays': 7}
                        }]
                    }
                )
                self.log(f"   [OK] Bucket created with versioning", style=self.STYLE_SUCCESS)
            else:
                raise

    def _export_database(self):
        """Export database using Django's dumpdata with compression"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_file = self.backup_dir / f"backup_{timestamp}.json"
        backup_file = self.backup_dir / f"backup_{timestamp}.json.gz"
        
        self.log(f"[2/6] Exporting database to {backup_file.name}")
        
        try:
            # Build exclude list
            exclude_args = []
            for app in self.exclude_apps:
                exclude_args.extend(['--exclude', app])
            
            # Export to JSON
            self.log("   -> Dumping data to JSON...")
            with open(json_file, 'w', encoding='utf-8') as f:
                call_command(
                    'dumpdata',
                    *exclude_args,
                    indent=2,
                    use_natural_foreign_keys=True,
                    use_natural_primary_keys=True,
                    stdout=f
                )
            
            json_size = json_file.stat().st_size
            self.log(f"   [OK] JSON export complete ({json_size / (1024*1024):.2f} MB)")
            
            # Compress with progress
            self.log("   -> Compressing file...")
            with open(json_file, 'rb') as f_in:
                with gzip.open(backup_file, 'wb', compresslevel=9) as f_out:
                    with tqdm(total=json_size, desc="      Progress", unit="B", unit_scale=True, 
                              leave=False, colour="green", dynamic_ncols=True) as pbar:
                        while True:
                            chunk = f_in.read(65536)
                            if not chunk:
                                break
                            f_out.write(chunk)
                            pbar.update(len(chunk))
            
            # Remove uncompressed file
            json_file.unlink()
            
            compressed_size = backup_file.stat().st_size
            ratio = (1 - compressed_size / json_size) * 100
            
            self.log(f"   [OK] Compression complete ({compressed_size / (1024*1024):.2f} MB, {ratio:.1f}% reduced)", 
                     style=self.STYLE_SUCCESS)
            
            return backup_file
            
        except Exception as e:
            if json_file.exists(): json_file.unlink()
            if backup_file.exists(): backup_file.unlink()
            raise CommandError(f"Export failed: {e}")

    def _calculate_checksum(self, file_path):
        """Calculate SHA256 checksum with progress"""
        self.log("[3/6] Calculating SHA256 checksum")
        
        sha256_hash = hashlib.sha256()
        file_size = file_path.stat().st_size
        
        with open(file_path, "rb") as f:
            with tqdm(total=file_size, desc="      Hashing", unit="B", unit_scale=True, 
                      leave=False, colour="cyan", dynamic_ncols=True) as pbar:
                for chunk in iter(lambda: f.read(65536), b""):
                    sha256_hash.update(chunk)
                    pbar.update(len(chunk))
        
        checksum = sha256_hash.hexdigest()
        self.log(f"   [OK] Checksum: {checksum[:16]}...", style=self.STYLE_SUCCESS)
        return checksum

    def _verify_backup(self, file_path):
        """Verify backup integrity"""
        self.log("[4/6] Verifying archive integrity")
        
        try:
            with gzip.open(file_path, 'rb') as f:
                f.read(1024 * 1024) # Test read first MB
            self.log("   [OK] Integrity check passed", style=self.STYLE_SUCCESS)
        except Exception as e:
            raise CommandError(f"Integrity verification failed: {e}")

    def _upload_to_s3(self, file_path, checksum):
        """Upload backup to S3 with progress"""
        s3_key = f"backups/{file_path.name}"
        self.log(f"[5/6] Uploading to S3: {s3_key}")
        
        file_size = file_path.stat().st_size
        
        try:
            with tqdm(total=file_size, desc="      Uploading", unit="B", unit_scale=True, 
                      leave=False, colour="blue", dynamic_ncols=True) as pbar:
                
                self.s3_client.upload_file(
                    str(file_path),
                    self.bucket_name,
                    s3_key,
                    ExtraArgs={
                        'Metadata': {
                            'checksum-sha256': checksum,
                            'backup-date': datetime.now().isoformat(),
                        },
                        'StorageClass': 'STANDARD_IA'
                    },
                    Callback=lambda b: pbar.update(b)
                )
            
            # Verify upload size
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            if response['ContentLength'] != file_size:
                raise CommandError("Upload size mismatch!")
            
            self.log(f"   [OK] Upload successful", style=self.STYLE_SUCCESS)
            return {'s3_key': s3_key, 'size': file_size}
            
        except Exception as e:
            raise CommandError(f"Upload failed: {e}")

    def _cleanup_old_backups(self):
        """Remove old local backups"""
        self.log(f"[6/6] Cleaning up local backups (> {self.keep_local_days} days)")
        
        cutoff = time.time() - (self.keep_local_days * 86400)
        deleted = 0
        
        for f in self.backup_dir.glob("backup_*.json.gz"):
            if f.stat().st_mtime < cutoff:
                f.unlink()
                deleted += 1
        
        self.log(f"   [OK] Removed {deleted} old local files", style=self.STYLE_SUCCESS)

