$ErrorActionPreference = "Stop"

Write-Host "Loading .env..."
try {
    Get-Content ..\.env | ForEach-Object {
        if ($_ -match 'AWS_KEY_ID=(.*)') { 
            $val = $matches[1].Trim()
            $env:AWS_ACCESS_KEY_ID = $val
            Write-Host "Set AWS_ACCESS_KEY_ID"
        }
        if ($_ -match 'AWS_KEY_SECRET=(.*)') { 
            $val = $matches[1].Trim()
            $env:AWS_SECRET_ACCESS_KEY = $val
            Write-Host "Set AWS_SECRET_ACCESS_KEY"
        }
    }
}
catch {
    Write-Error "Failed to read .env file"
    exit 1
}

Write-Host "Verifying Identity..."
try {
    $env:PAGER = "" # Avoid AWS CLI pager issues
    aws sts get-caller-identity
}
catch {
    Write-Error "Failed to verify identity. Check credentials."
    exit 1
}

Write-Host "Starting Deployment..."
# Run CDK deploy. npx ensures aws-cdk is available.
# We pipe 'y' to npx just in case it asks for package installation, though --require-approval never handles stack approval.
# Wait, piping 'y' to npx might be risky if it consumes stdin for other things? 
# Better: Set CI=true environment variable which often suppresses interactive prompts or fails fast.
# Run local CDK deploy.
$env:CI = "true" 
npm run deploy
if ($LASTEXITCODE -ne 0) {
    Write-Error "Deployment failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}
Write-Host "Deployment Completed Successfully"
