# Deployment Guide

This guide walks you through deploying Etsy Assistant from scratch — AWS account creation through to a running app.

**Estimated time**: 30-45 minutes
**Estimated cost**: ~$1-5/month (mostly within free tier)

---

## Prerequisites

You need these tools installed on your **local machine** (not this remote session):

1. **AWS CLI v2**: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html
2. **AWS SAM CLI**: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html
3. **Docker Desktop**: https://www.docker.com/products/docker-desktop/
4. **Node.js 22+**: https://nodejs.org/
5. **Git**: to clone the repo

---

## Step 1: Create an AWS Account

1. Go to https://aws.amazon.com/ and click **Create an AWS Account**
2. Enter your email, choose a root account name, verify email
3. Enter payment info (required, but free tier covers almost everything)
4. Choose the **Basic (Free)** support plan
5. Wait for account activation (usually instant, sometimes up to 24 hours)

---

## Step 2: Create an IAM User for Deployment

Don't use your root account for deployment. Create a dedicated IAM user:

1. Go to **IAM Console**: https://console.aws.amazon.com/iam/
2. Click **Users** → **Create user**
3. Name: `etsy-assistant-deploy`
4. Check **Provide user access to the AWS Management Console** (optional)
5. Click **Next** → **Attach policies directly**
6. Attach these policies:
   - `AmazonS3FullAccess`
   - `AmazonDynamoDBFullAccess`
   - `AWSLambda_FullAccess`
   - `AmazonAPIGatewayAdministrator`
   - `AmazonEC2ContainerRegistryFullAccess`
   - `AWSCloudFormationFullAccess`
   - `IAMFullAccess` (needed for SAM to create Lambda execution roles)
7. Click **Create user**
8. Go to the user → **Security credentials** → **Create access key**
9. Choose **Command Line Interface (CLI)**
10. Save the **Access Key ID** and **Secret Access Key**

---

## Step 3: Configure AWS CLI

```bash
aws configure
```

Enter:
- **AWS Access Key ID**: from step 2
- **AWS Secret Access Key**: from step 2
- **Default region**: `us-east-1` (recommended)
- **Output format**: `json`

Verify it works:
```bash
aws sts get-caller-identity
```

---

## Step 4: Get an Anthropic API Key

The listing generation feature uses Claude Vision. Get an API key:

1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Go to **API Keys** → **Create Key**
4. Save the key (starts with `sk-ant-...`)

---

## Step 5: Deploy the Backend

Clone the repo and run the deploy script:

```bash
git clone https://github.com/paleyzpl/EstyAssistant.git
cd EstyAssistant

# Set your Anthropic API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Set the frontend URL (update after Vercel deploy)
export CORS_ORIGINS="http://localhost:3000"

# Deploy!
./scripts/deploy-backend.sh
```

The script will:
1. Create an ECR repository for the Docker image
2. Build the Docker image with OpenCV + FastAPI
3. Push to ECR
4. Deploy via SAM (Lambda + API Gateway + S3 + DynamoDB)

At the end, you'll see:
```
  API URL:    https://abc123.execute-api.us-east-1.amazonaws.com
  S3 Bucket:  etsy-assistant-images-123456789012
```

**Save the API URL** — you'll need it for the frontend.

### Verify the backend

```bash
curl https://abc123.execute-api.us-east-1.amazonaws.com/health
# Should return: {"status":"ok"}
```

---

## Step 6: Deploy the Frontend to Vercel

1. Go to https://vercel.com/ and sign up with your GitHub account
2. Click **Add New Project**
3. Import the `paleyzpl/EstyAssistant` repository
4. Configure:
   - **Framework Preset**: Next.js (auto-detected)
   - **Root Directory**: `frontend` (click "Edit" and type `frontend`)
   - **Environment Variables**: Add:
     - `NEXT_PUBLIC_API_URL` = `https://abc123.execute-api.us-east-1.amazonaws.com` (your API URL from step 5)
5. Click **Deploy**

Vercel will build and deploy. You'll get a URL like `https://etsy-assistant-xyz.vercel.app`.

---

## Step 7: Update CORS

Now that you have the Vercel URL, update the backend to allow it:

```bash
export CORS_ORIGINS="https://etsy-assistant-xyz.vercel.app,http://localhost:3000"
export ANTHROPIC_API_KEY="sk-ant-..."
./scripts/deploy-backend.sh
```

---

## Step 8: Test End-to-End

1. Open your Vercel URL in a browser
2. Drop a sketch photo into the upload area
3. Select print sizes (e.g., 8x10)
4. Click **Process Sketch**
5. You should see before/after preview and download links

---

## Local Development

You can still run everything locally for development:

```bash
# Terminal 1: Backend (port 8000)
cd backend
uv sync --group dev
PYTHONPATH=../src:src S3_BUCKET=your-bucket AWS_REGION=us-east-1 \
    uvicorn api.main:app --reload

# Terminal 2: Frontend (port 3000)
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

Note: Local backend still needs real AWS credentials for S3 access.

---

## Updating

After making code changes:

```bash
# Backend: rebuild and deploy
./scripts/deploy-backend.sh

# Frontend: just push to GitHub — Vercel auto-deploys
git push origin main
```

---

## Costs Breakdown

| Service | Free Tier | After Free Tier |
|---------|-----------|----------------|
| Lambda | 1M requests + 400K GB-s/month | ~$0/month at low volume |
| API Gateway | 1M calls/month (12 months) | ~$0 |
| S3 | 5 GB (12 months) | ~$0.50/month |
| DynamoDB | 25 GB + 25 RCU/WCU | ~$0 |
| ECR | 500 MB | ~$0 |
| Vercel | Free hobby tier | $0 |
| Anthropic API | Pay-per-use | ~$0.05-0.10 per image |
| **Total** | | **~$1-5/month** |

---

## Troubleshooting

### "Access Denied" on S3 upload
Check that the Lambda execution role has S3 permissions. The SAM template handles this automatically.

### CORS errors in browser
Make sure `CORS_ORIGINS` in the deploy script matches your Vercel URL exactly (including `https://`).

### Lambda timeout
Default is 60 seconds. If processing large images takes longer, increase `Timeout` in `infra/template.yaml`.

### Docker build fails on M1/M2 Mac
Add `--platform linux/amd64` to the docker build command in `deploy-backend.sh`:
```bash
docker build --platform linux/amd64 -f backend/Dockerfile -t "$IMAGE_TAG" .
```

---

## Tear Down

To remove everything and stop charges:

```bash
# Delete the SAM stack (Lambda, API Gateway, DynamoDB)
aws cloudformation delete-stack --stack-name etsy-assistant --region us-east-1

# Empty and delete the S3 bucket
aws s3 rb s3://etsy-assistant-images-ACCOUNT_ID --force

# Delete the ECR repository
aws ecr delete-repository --repository-name etsy-assistant --force --region us-east-1
```

Delete the Vercel project from the Vercel dashboard.
