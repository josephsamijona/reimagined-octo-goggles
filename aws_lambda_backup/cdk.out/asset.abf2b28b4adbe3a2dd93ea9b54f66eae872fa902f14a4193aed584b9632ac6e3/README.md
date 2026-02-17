# AWS Lambda Database Backup - Deployment Guide

This directory contains a standalone AWS Lambda function packaged as a Docker container to backup a MySQL/MariaDB database to S3.

## Prerequisites
- AWS CLI installed and configured.
- Docker installed.
- An S3 Bucket for backups (e.g., `jhbridge-mysql-backups`).
- AWS Secrets Manager secret created.

## 1. Secrets Manager Setup
Create a secret named `prod/jhbridge/db` (or custom name) with the following key/value pairs:
- `host`: Database hostname (e.g., `roundhouse.proxy.rlwy.net`)
- `port`: Database port (e.g., `3306`)
- `username`: Database user
- `password`: Database password
- `dbname`: Database name (optional, if omitted dumps all DBs)

## 2. Build and Push Docker Image
```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# Create Repository (if not exists)
aws ecr create-repository --repository-name backup-lambda

# Build
docker build -t backup-lambda .

# Tag
docker tag backup-lambda:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/backup-lambda:latest

# Push
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/backup-lambda:latest
```

## 3. Create Lambda Function
- **Function Name**: `db-backup-worker`
- **Package Type**: Container Image (Select the image pushed above).
- **Architecture**: x86_64 (matches build) or arm64 if you built for arm.

### Configuration (Crucial for Large DBs)
- **Memory**: `1024 MB` (Increases network performance).
- **Ephemeral Storage**: `5120 MB` (5GB) or more. **Required for databases > 500MB.**
- **Timeout**: `15 minutes` (900 seconds).

### Environment Variables
- `SECRET_NAME`: `prod/jhbridge/db`
- `BACKUP_BUCKET_NAME`: `jhbridge-mysql-backups`

### Permissions (IAM Role)
Attach a policy allowing:
- `s3:PutObject` on `arn:aws:s3:::jhbridge-mysql-backups/*`
- `secretsmanager:GetSecretValue` on `arn:aws:secretsmanager:*:*:secret:prod/jhbridge/db-*`

## 4. Schedule (EventBridge)
- Create an EventBridge Schedule.
- **Schedule**: `Cron expression` -> `0 9 * * ? *` (Daily at 9:00 UTC).
- **Target**: Lambda Function -> `db-backup-worker`.

## Safety & Cost
- **Network**: Run OUTSIDE VPC to avoid NAT Gateway costs (Database must be public).
- **Cost**: ~$0.50/month (Secrets Manager + Storage).

## 5. Deployment via AWS CDK (Recommended)
We have provided a CDK app to automate the deployment of the Lambda, Role, and Schedule.

### Prerequisites
- Node.js & npm installed (for CDK CLI).
- Python 3 installed.
- AWS CLI configured.

### Steps
1.  **Install AWS CDK CLI**:
    ```bash
    npm install -g aws-cdk
    ```

2.  **Setup Python Environment**:
    ```bash
    cd aws_lambda_backup
    python -m venv .venv
    source .venv/bin/activate  # Windows: .venv\Scripts\activate
    pip install -r cdk_requirements.txt
    ```

3.  **Deploy**:
    ```bash
    cdk deploy
    ```
    This will:
    - Build the Docker image from `.`
    - Push it to a CDK-managed ECR repository.
    - Create the Lambda function with 5GB storage.
    - Setup the IAM Role and EventBridge Rule.

