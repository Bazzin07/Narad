# Narad — AWS Deployment Guide

**Architecture: 5 AWS Services | ~$46/month | Hackathon-optimized**

```
Frontend:  AWS Amplify (Next.js)          ~$0/mo
Backend:   AWS App Runner (FastAPI)       ~$25/mo  
Database:  Amazon RDS PostgreSQL          ~$14/mo  (includes pgvector — replaces FAISS)
AI/LLMs:   AWS Bedrock (Claude + Titan)   ~$5/mo
Registry:  AWS ECR (Docker images)        ~$1/mo
                                  TOTAL: ~$45/mo
```

---

## Prerequisites

```bash
# 1. Install AWS CLI and authenticate
brew install awscli
aws configure  # Enter your Access Key, Secret Key, and region (us-east-1)

# 2. Make sure Docker is running
docker --version
```

---

## Step 1: Create an ECR Repository

```bash
# Create the repository
aws ecr create-repository --repository-name narad-backend --region us-east-1

# Capture the registry URI (looks like: 123456789012.dkr.ecr.us-east-1.amazonaws.com)
REGISTRY=$(aws ecr describe-repositories --repository-names narad-backend \
  --query 'repositories[0].repositoryUri' --output text | cut -d/ -f1)
echo "Registry: $REGISTRY"
```

---

## Step 2: Build and Push the Backend Docker Image

```bash
cd /path/to/Narad/backend

# Authenticate Docker with ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $REGISTRY

# Build the image (takes ~5-10 min first time due to spaCy models)
docker build -t narad-backend .

# Tag and push
docker tag narad-backend:latest $REGISTRY/narad-backend:latest
docker push $REGISTRY/narad-backend:latest
echo "Image URI: $REGISTRY/narad-backend:latest"
```

---

## Step 3: Deploy the VPC Network

```bash
cd /path/to/Narad/cloudformation

aws cloudformation deploy \
  --template-file lean-vpc-network.yaml \
  --stack-name narad-vpc \
  --capabilities CAPABILITY_IAM
```

---

## Step 4: Deploy the RDS Database

```bash
# Generate a strong password
DB_PASSWORD=$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 24)
echo "Save this password securely: $DB_PASSWORD"

aws cloudformation deploy \
  --template-file rds-pgvector.yaml \
  --stack-name narad-rds \
  --parameter-overrides \
    DBPassword=$DB_PASSWORD \
    DBName=narad \
  --capabilities CAPABILITY_IAM

# Get the RDS endpoint after deployment (~5 min)
RDS_HOST=$(aws cloudformation describe-stacks --stack-name narad-rds \
  --query 'Stacks[0].Outputs[?OutputKey==`DBEndpoint`].OutputValue' \
  --output text)
echo "RDS Host: $RDS_HOST"

# Build the DATABASE_URL
DATABASE_URL="postgresql+asyncpg://narad:$DB_PASSWORD@$RDS_HOST:5432/narad"
echo "DATABASE_URL: $DATABASE_URL"
```

---

## Step 5: Enable pgvector on the Database

Connect to the RDS instance and enable the pgvector extension:

```bash
# Install psql client if needed
brew install postgresql

# Connect (you may need to temporarily allow public access in the RDS security group)
psql "host=$RDS_HOST port=5432 dbname=narad user=narad password=$DB_PASSWORD sslmode=require"

# Run inside psql:
CREATE EXTENSION IF NOT EXISTS vector;
\q
```

---

## Step 6: Deploy the App Runner Backend

```bash
IMAGE_URI="$REGISTRY/narad-backend:latest"

aws cloudformation deploy \
  --template-file app-runner.yaml \
  --stack-name narad-apprunner \
  --parameter-overrides \
    ECRImageURI=$IMAGE_URI \
    DatabaseURL=$DATABASE_URL \
  --capabilities CAPABILITY_NAMED_IAM

# Get the backend URL
BACKEND_URL=$(aws cloudformation describe-stacks --stack-name narad-apprunner \
  --query 'Stacks[0].Outputs[?OutputKey==`AppRunnerURL`].OutputValue' \
  --output text)
echo "Backend URL: https://$BACKEND_URL"
```

---

## Step 7: Deploy the Frontend to AWS Amplify

1. Push your code to a GitHub/GitLab repository.
2. Go to AWS Console → **Amplify** → **New App** → **Host Web App**.
3. Connect your GitHub repo and select the `frontend/` folder as the root.
4. Amplify will detect the `amplify.yml` build spec automatically.
5. Set this environment variable in Amplify settings:
   ```
   NEXT_PUBLIC_API_URL = https://<your-app-runner-url>
   ```
6. Deploy and your frontend is live globally on a CDN!

---

## Step 8: Post-Deployment Verification

```bash
# Test the backend health check
curl https://$BACKEND_URL/health

# Trigger the initial data ingestion
curl -X POST https://$BACKEND_URL/api/news/ingest

# Verify articles are being stored
curl https://$BACKEND_URL/api/news?limit=5
```

---

## Environment Variables for App Runner

The App Runner CloudFormation template injects these automatically:

| Variable | Value |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string to RDS |
| `LLM_BACKEND` | `bedrock` |
| `BEDROCK_MODEL_ID_FAST` | Claude Haiku 4.5 |
| `BEDROCK_MODEL_ID` | Claude Sonnet 3.5 |
| `EMBEDDING_BACKEND` | `titan` (Amazon Titan Embeddings V2) |
| `TITAN_EMBEDDING_MODEL_ID` | `amazon.titan-embed-text-v2:0` |
| `AWS_REGION` | `us-east-1` |
| `KMP_DUPLICATE_LIB_OK` | `TRUE` |

---

## Cost Monitoring

Set up a billing alert to stay under your budget:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name NaradBudgetAlert \
  --alarm-description "Alert when monthly AWS spend exceeds $70" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --threshold 70 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:<your-account-id>:<your-sns-topic>
```
