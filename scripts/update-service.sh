#!/bin/bash

# Update ECS service with new Docker image

set -e

ENVIRONMENT_NAME="narad-prod"
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Parse arguments
SERVICE=$1

if [ -z "$SERVICE" ]; then
    echo "Usage: ./scripts/update-service.sh [backend|frontend]"
    exit 1
fi

echo "Updating ${SERVICE} service..."

# Build and push new image
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ENVIRONMENT_NAME}-${SERVICE}"

# Login to ECR
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Build and push
cd ${SERVICE}
docker build -t ${ENVIRONMENT_NAME}-${SERVICE}:latest .
docker tag ${ENVIRONMENT_NAME}-${SERVICE}:latest ${ECR_URI}:latest
docker push ${ECR_URI}:latest
cd ..

# Force new deployment
aws ecs update-service \
    --cluster ${ENVIRONMENT_NAME}-cluster \
    --service ${ENVIRONMENT_NAME}-${SERVICE} \
    --force-new-deployment \
    --region ${AWS_REGION}

echo "${SERVICE} service update initiated!"
echo "Monitor deployment: aws ecs describe-services --cluster ${ENVIRONMENT_NAME}-cluster --services ${ENVIRONMENT_NAME}-${SERVICE} --region ${AWS_REGION}"
