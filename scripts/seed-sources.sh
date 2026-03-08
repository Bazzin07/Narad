#!/bin/bash

# Seed initial sources data

set -e

ENVIRONMENT_NAME="narad-prod"
AWS_REGION="us-east-1"

echo "Seeding initial sources..."

# Get the Load Balancer URL
ALB_DNS=$(aws cloudformation describe-stacks \
    --stack-name ${ENVIRONMENT_NAME}-ecs \
    --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' \
    --output text \
    --region ${AWS_REGION})

# Trigger initial ingestion (this will seed sources automatically)
curl -X POST "http://${ALB_DNS}/api/news/ingest" \
    -H "Content-Type: application/json" \
    -d '{}'

echo "Sources seeded and initial ingestion started!"
