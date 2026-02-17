from aws_cdk import (
    Stack,
    Duration,
    Size,
    aws_lambda as _lambda,
    aws_s3 as s3,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
)
from constructs import Construct

class BackupStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Reference Existing Assets
        # Secret Name for DB Credentials (Must exist in Secrets Manager)
        secret_name = "prod/jhbridge/db"
        
        # Reference Existing Bucket
        bucket = s3.Bucket.from_bucket_name(
            self, 
            "BackupBucket", 
            "jhbridge-mysql-backups"
        )

        # 2. Define Lambda Function from Docker Image
        # Images are built from local Dockerfile
        backup_fn = _lambda.DockerImageFunction(
            self, "BackupFunction",
            code=_lambda.DockerImageCode.from_image_asset("."),
            timeout=Duration.minutes(15),
            memory_size=1024, # 1GB Memory
            ephemeral_storage_size=Size.mebibytes(5120), # 5GB Storage
            environment={
                "SECRET_NAME": secret_name,
                "BACKUP_BUCKET_NAME": bucket.bucket_name
            },
            architecture=_lambda.Architecture.X86_64,
        )
        
        # Fix for ephemeral storage in older CDK or direct property usage if Construct library varies
        # reliable way via escape hatch or modern property if available. 
        # Using L1 construct override if needed, but let's assume valid prop for now.
        # Note: ephemeral_storage_size argument needs to be Size object in recent CDK.
        # verifying via generic override to be safe if specific version unknown
        cfn_fn = backup_fn.node.default_child
        cfn_fn.ephemeral_storage = {"size": 5120}

        # 3. Grant Permissions
        bucket.grant_put(backup_fn)
        
        # Grant Secret Access manually (as we don't have the Secret object, just name)
        # We construct the ARN pattern or use a wildcard for the specific secret name
        backup_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["secretsmanager:GetSecretValue"],
            resources=[f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:{secret_name}-*"]
        ))

        # 4. Schedule (EventBridge)
        # Run at 09:00 UTC daily
        rule = events.Rule(
            self, "BackupSchedule",
            schedule=events.Schedule.cron(minute="0", hour="9")
        )
        rule.add_target(targets.LambdaFunction(backup_fn))
