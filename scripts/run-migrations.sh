#!/bin/bash

# Run database migrations on ECS

set -e

ENVIRONMENT_NAME="narad-prod"
AWS_REGION="us-east-1"

echo "Running database migrations..."

# Get cluster and task definition
CLUSTER="${ENVIRONMENT_NAME}-cluster"
TASK_DEFINITION="${ENVIRONMENT_NAME}-backend"

# Get subnet and security group
SUBNET=$(aws cloudformation describe-stacks \
    --stack-name ${ENVIRONMENT_NAME}-vpc \
    --query 'Stacks[0].Outputs[?OutputKey==`PrivateSubnet1`].OutputValue' \
    --output text \
    --region ${AWS_REGION})

SECURITY_GROUP=$(aws cloudformation describe-stacks \
    --stack-name ${ENVIRONMENT_NAME}-database \
    --query 'Stacks[0].Outputs[?OutputKey==`ECSSecurityGroup`].OutputValue' \
    --output text \
    --region ${AWS_REGION})

# Run migration task
TASK_ARN=$(aws ecs run-task \
    --cluster ${CLUSTER} \
    --task-definition ${TASK_DEFINITION} \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[${SUBNET}],securityGroups=[${SECURITY_GROUP}],assignPublicIp=DISABLED}" \
    --overrides '{"containerOverrides":[{"name":"backend","command":["alembic","upgrade","head"]}]}' \
    --region ${AWS_REGION} \
    --query 'tasks[0].taskArn' \
    --output text)

echo "Migration task started: ${TASK_ARN}"
echo "Waiting for task to complete..."

aws ecs wait tasks-stopped \
    --cluster ${CLUSTER} \
    --tasks ${TASK_ARN} \
    --region ${AWS_REGION}

echo "Migration complete!"
