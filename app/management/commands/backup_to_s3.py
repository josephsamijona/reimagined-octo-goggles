"""
Django Management Command: Backup Database to AWS S3
Safely exports Django database to AWS S3 using dumpdata (no mysqldump required)
"""

import os
import gzip
import hashlib
import tempfile
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

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("DJANGO DATABASE BACKUP TO AWS S3"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

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
            
            # Execute backup process
            self._create_s3_bucket()
            backup_file = self._export_database()
            checksum = self._calculate_checksum(backup_file)
            self._verify_backup(backup_file)
            upload_info = self._upload_to_s3(backup_file, checksum)
            self._cleanup_old_backups()
            
            # Success summary
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.SUCCESS("BACKUP COMPLETED SUCCESSFULLY ✓"))
            self.stdout.write("=" * 80)
            self.stdout.write(f"Local file: {backup_file}")
            self.stdout.write(f"S3 location: s3://{self.bucket_name}/{upload_info['s3_key']}")
            self.stdout.write(f"File size: {upload_info['size'] / (1024*1024):.2f} MB")
            self.stdout.write(f"Checksum: {checksum}")
            self.stdout.write(f"Download URL (7 days): {upload_info['download_url'][:80]}...")
            
        except Exception as e:
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.ERROR(f"BACKUP FAILED: {e}"))
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
        self.stdout.write(f"[1/5] Checking/Creating S3 bucket: {self.bucket_name}")
        
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            self.stdout.write(self.style.SUCCESS(f"✓ Bucket '{self.bucket_name}' exists"))
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                self.stdout.write(f"Creating bucket '{self.bucket_name}'...")
                
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
                
                self.stdout.write(self.style.SUCCESS("✓ Bucket created with versioning"))
            else:
                raise

    def _export_database(self):
        """Export database using Django's dumpdata"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_file = self.backup_dir / f"backup_{timestamp}.json"
        backup_file = self.backup_dir / f"backup_{timestamp}.json.gz"
        
        self.stdout.write(f"[2/5] Exporting database: {backup_file.name}")
        
        try:
            # Build exclude list
            exclude_list = []
            for app in self.exclude_apps:
                exclude_list.extend(['--exclude', app])
            
            # Export to JSON
            self.stdout.write("Running dumpdata...")
            with open(json_file, 'w', encoding='utf-8') as f:
                call_command(
                    'dumpdata',
                    *exclude_list,
                    indent=2,
                    use_natural_foreign_keys=True,
                    use_natural_primary_keys=True,
                    stdout=f
                )
            
            json_size = json_file.stat().st_size
            self.stdout.write(f"JSON export: {json_size / (1024*1024):.2f} MB")
            
            # Compress with progress
            self.stdout.write("Compressing...")
            with open(json_file, 'rb') as f_in:
                with gzip.open(backup_file, 'wb', compresslevel=9) as f_out:
                    with tqdm(total=json_size, desc="Compressing", unit="B", unit_scale=True, ncols=100) as pbar:
                        while True:
                            chunk = f_in.read(8192)
                            if not chunk:
                                break
                            f_out.write(chunk)
                            pbar.update(len(chunk))
            
            # Remove uncompressed file
            json_file.unlink()
            
            compressed_size = backup_file.stat().st_size
            compression_ratio = (1 - compressed_size / json_size) * 100
            
            self.stdout.write(self.style.SUCCESS(
                f"✓ Backup created: {compressed_size / (1024*1024):.2f} MB "
                f"(compression: {compression_ratio:.1f}%)"
            ))
            
            return backup_file
            
        except Exception as e:
            if json_file.exists():
                json_file.unlink()
            if backup_file.exists():
                backup_file.unlink()
            raise CommandError(f"Export failed: {e}")

    def _calculate_checksum(self, file_path):
        """Calculate SHA256 checksum"""
        self.stdout.write("[3/5] Calculating checksum...")
        
        sha256_hash = hashlib.sha256()
        file_size = file_path.stat().st_size
        
        with open(file_path, "rb") as f:
            with tqdm(total=file_size, desc="Computing checksum", unit="B", unit_scale=True, ncols=100) as pbar:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
                    pbar.update(len(byte_block))
        
        checksum = sha256_hash.hexdigest()
        self.stdout.write(self.style.SUCCESS(f"✓ Checksum: {checksum}"))
        return checksum

    def _verify_backup(self, file_path):
        """Verify backup integrity"""
        self.stdout.write("[4/5] Verifying backup integrity...")
        
        try:
            # Test gzip decompression
            with gzip.open(file_path, 'rb') as f:
                # Read first 1KB to verify it's valid gzip
                f.read(1024)
            
            self.stdout.write(self.style.SUCCESS("✓ Backup integrity verified"))
            
        except Exception as e:
            raise CommandError(f"Backup verification failed: {e}")

    def _upload_to_s3(self, file_path, checksum):
        """Upload backup to S3"""
        s3_key = f"backups/{file_path.name}"
        
        self.stdout.write(f"[5/5] Uploading to S3: s3://{self.bucket_name}/{s3_key}")
        
        file_size = file_path.stat().st_size
        
        try:
            # Upload with progress
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
                            'django-version': settings.VERSION if hasattr(settings, 'VERSION') else 'unknown',
                            'format': 'json-gzip'
                        },
                        'StorageClass': 'STANDARD_IA'
                    },
                    Callback=upload_callback
                )
            
            # Verify upload
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            uploaded_size = response['ContentLength']
            
            if uploaded_size != file_size:
                raise CommandError(f"Upload verification failed: size mismatch")
            
            self.stdout.write(self.style.SUCCESS(f"✓ Upload successful: {uploaded_size / (1024*1024):.2f} MB"))
            
            # Generate download URL
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
            raise CommandError(f"Upload failed: {e}")

    def _cleanup_old_backups(self):
        """Remove old local backups"""
        self.stdout.write(f"Cleaning up local backups older than {self.keep_local_days} days...")
        
        cutoff_time = datetime.now().timestamp() - (self.keep_local_days * 86400)
        deleted = 0
        
        for backup_file in self.backup_dir.glob("backup_*.json.gz"):
            if backup_file.stat().st_mtime < cutoff_time:
                backup_file.unlink()
                deleted += 1
        
        self.stdout.write(self.style.SUCCESS(f"✓ Cleaned up {deleted} old backup(s)"))
