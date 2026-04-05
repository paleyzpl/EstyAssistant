#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────
# Etsy Assistant — Backend Deploy Script
# Builds Docker image, pushes to ECR, deploys via SAM
# Run from the repo root: ./scripts/deploy-backend.sh
# ──────────────────────────────────────────────

STACK_NAME="${STACK_NAME:-etsy-assistant}"
REGION="${AWS_REGION:-us-east-1}"
ECR_REPO="${ECR_REPO:-etsy-assistant}"
CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:3000}"
ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"

echo "==> Checking prerequisites..."
command -v aws >/dev/null 2>&1 || { echo "ERROR: aws CLI not found. Install: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html"; exit 1; }
command -v sam >/dev/null 2>&1 || { echo "ERROR: sam CLI not found. Install: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "ERROR: docker not found."; exit 1; }

# Verify AWS credentials
aws sts get-caller-identity --region "$REGION" > /dev/null || { echo "ERROR: AWS credentials not configured. Run: aws configure"; exit 1; }
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "    AWS Account: $ACCOUNT_ID"
echo "    Region:      $REGION"

# Create ECR repository if it doesn't exist
echo "==> Ensuring ECR repository exists..."
aws ecr describe-repositories --repository-names "$ECR_REPO" --region "$REGION" 2>/dev/null || \
    aws ecr create-repository --repository-name "$ECR_REPO" --region "$REGION" --image-scanning-configuration scanOnPush=true

# Login to ECR
echo "==> Logging into ECR..."
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

# Build Docker image
IMAGE_TAG="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO:latest"
echo "==> Building Docker image..."
docker build -f backend/Dockerfile -t "$IMAGE_TAG" .

# Push to ECR
echo "==> Pushing to ECR..."
docker push "$IMAGE_TAG"

# Deploy with SAM
echo "==> Deploying with SAM..."
cd infra
sam build
sam deploy \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --resolve-image-repos \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides \
        "CorsOrigins=$CORS_ORIGINS" \
        "AnthropicApiKey=$ANTHROPIC_API_KEY" \
    --no-confirm-changeset

# Get outputs
echo ""
echo "==> Deployment complete!"
API_URL=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' --output text)
BUCKET=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' --output text)

echo "────────────────────────────────────"
echo "  API URL:    $API_URL"
echo "  S3 Bucket:  $BUCKET"
echo "────────────────────────────────────"
echo ""
echo "Set this in your frontend .env.local:"
echo "  NEXT_PUBLIC_API_URL=$API_URL"
