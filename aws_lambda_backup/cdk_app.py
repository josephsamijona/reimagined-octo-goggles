#!/usr/bin/env python3
import os
import aws_cdk as cdk
from cdk_stack import BackupStack

app = cdk.App()

# Environment-agnostic stack or specific account/region
env = cdk.Environment(
    account=os.getenv('CDK_DEFAULT_ACCOUNT'), 
    region=os.getenv('CDK_DEFAULT_REGION')
)

BackupStack(app, "JhbridgeBackupStack", env=env)

app.synth()
