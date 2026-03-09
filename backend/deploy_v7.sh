#!/bin/bash
set -e

echo "🚀 Building x86_64 Docker image for App Runner..."
docker buildx build --platform linux/amd64 -t narad-backend-amd64:latest .

echo "🏷️ Tagging image as v7-amd64..."
docker tag narad-backend-amd64:latest 115179823356.dkr.ecr.us-east-1.amazonaws.com/narad-backend:v7-amd64

echo "🔑 Authenticating with AWS ECR..."
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 115179823356.dkr.ecr.us-east-1.amazonaws.com

echo "📤 Pushing image to ECR..."
docker push 115179823356.dkr.ecr.us-east-1.amazonaws.com/narad-backend:v7-amd64

echo "🔄 Updating App Runner Service to v7-amd64..."
aws apprunner update-service \
    --service-arn "arn:aws:apprunner:us-east-1:115179823356:service/narad-prod-backend/91450accf51c427a9b1dabef42f1001d" \
    --source-configuration '{"ImageRepository":{"ImageIdentifier":"115179823356.dkr.ecr.us-east-1.amazonaws.com/narad-backend:v7-amd64","ImageRepositoryType":"ECR","ImageConfiguration":{"Port":"8000"}},"AuthenticationConfiguration":{"AccessRoleArn":"arn:aws:iam::115179823356:role/narad-prod-apprunner-ecr-role"}}' \
    --region us-east-1 \
    --query 'OperationId' \
    --output text

echo "✅ App Runner update initiated! Check AWS console for status."
