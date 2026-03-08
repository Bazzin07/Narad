#!/bin/bash

# Check deployment status

set -e

ENVIRONMENT_NAME="narad-prod"
AWS_REGION="us-east-1"

echo "========================================="
echo "Narad Deployment Status Check"
echo "========================================="

# Check CloudFormation stacks
echo -e "\n📦 CloudFormation Stacks:"
for stack in vpc database storage ecs; do
    STATUS=$(aws cloudformation describe-stacks \
        --stack-name ${ENVIRONMENT_NAME}-${stack} \
        --query 'Stacks[0].StackStatus' \
        --output text \
        --region ${AWS_REGION} 2>/dev/null || echo "NOT_FOUND")
    
    if [ "$STATUS" = "CREATE_COMPLETE" ] || [ "$STATUS" = "UPDATE_COMPLETE" ]; then
        echo "  ✅ ${stack}: ${STATUS}"
    elif [ "$STATUS" = "NOT_FOUND" ]; then
        echo "  ❌ ${stack}: NOT DEPLOYED"
    else
        echo "  ⚠️  ${stack}: ${STATUS}"
    fi
done

# Check ECS services
echo -e "\n🐳 ECS Services:"
for service in backend frontend; do
    RUNNING=$(aws ecs describe-services \
        --cluster ${ENVIRONMENT_NAME}-cluster \
        --services ${ENVIRONMENT_NAME}-${service} \
        --query 'services[0].runningCount' \
        --output text \
        --region ${AWS_REGION} 2>/dev/null || echo "0")
    
    DESIRED=$(aws ecs describe-services \
        --cluster ${ENVIRONMENT_NAME}-cluster \
        --services ${ENVIRONMENT_NAME}-${service} \
        --query 'services[0].desiredCount' \
        --output text \
        --region ${AWS_REGION} 2>/dev/null || echo "0")
    
    if [ "$RUNNING" = "$DESIRED" ] && [ "$RUNNING" != "0" ]; then
        echo "  ✅ ${service}: ${RUNNING}/${DESIRED} tasks running"
    elif [ "$RUNNING" = "0" ] && [ "$DESIRED" = "0" ]; then
        echo "  ⚠️  ${service}: Service scaled to 0"
    else
        echo "  ⚠️  ${service}: ${RUNNING}/${DESIRED} tasks running (not healthy)"
    fi
done

# Check RDS
echo -e "\n🗄️  RDS PostgreSQL:"
DB_STATUS=$(aws rds describe-db-instances \
    --db-instance-identifier ${ENVIRONMENT_NAME}-postgres \
    --query 'DBInstances[0].DBInstanceStatus' \
    --output text \
    --region ${AWS_REGION} 2>/dev/null || echo "NOT_FOUND")

if [ "$DB_STATUS" = "available" ]; then
    DB_ENDPOINT=$(aws rds describe-db-instances \
        --db-instance-identifier ${ENVIRONMENT_NAME}-postgres \
        --query 'DBInstances[0].Endpoint.Address' \
        --output text \
        --region ${AWS_REGION})
    echo "  ✅ Status: ${DB_STATUS}"
    echo "  📍 Endpoint: ${DB_ENDPOINT}"
elif [ "$DB_STATUS" = "NOT_FOUND" ]; then
    echo "  ❌ NOT DEPLOYED"
else
    echo "  ⚠️  Status: ${DB_STATUS}"
fi

# Check ElastiCache
echo -e "\n💾 ElastiCache Redis:"
REDIS_STATUS=$(aws elasticache describe-replication-groups \
    --replication-group-id ${ENVIRONMENT_NAME}-redis \
    --query 'ReplicationGroups[0].Status' \
    --output text \
    --region ${AWS_REGION} 2>/dev/null || echo "NOT_FOUND")

if [ "$REDIS_STATUS" = "available" ]; then
    REDIS_ENDPOINT=$(aws elasticache describe-replication-groups \
        --replication-group-id ${ENVIRONMENT_NAME}-redis \
        --query 'ReplicationGroups[0].NodeGroups[0].PrimaryEndpoint.Address' \
        --output text \
        --region ${AWS_REGION})
    echo "  ✅ Status: ${REDIS_STATUS}"
    echo "  📍 Endpoint: ${REDIS_ENDPOINT}"
elif [ "$REDIS_STATUS" = "NOT_FOUND" ]; then
    echo "  ❌ NOT DEPLOYED"
else
    echo "  ⚠️  Status: ${REDIS_STATUS}"
fi

# Check Load Balancer
echo -e "\n🌐 Application Load Balancer:"
ALB_DNS=$(aws cloudformation describe-stacks \
    --stack-name ${ENVIRONMENT_NAME}-ecs \
    --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' \
    --output text \
    --region ${AWS_REGION} 2>/dev/null || echo "NOT_FOUND")

if [ "$ALB_DNS" != "NOT_FOUND" ] && [ -n "$ALB_DNS" ]; then
    echo "  ✅ DNS: ${ALB_DNS}"
    echo "  🔗 URL: http://${ALB_DNS}"
    
    # Test health endpoint
    echo -e "\n🏥 Health Check:"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://${ALB_DNS}/health --max-time 5 2>/dev/null || echo "000")
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "  ✅ Backend health check passed"
    else
        echo "  ⚠️  Backend health check failed (HTTP ${HTTP_CODE})"
    fi
else
    echo "  ❌ NOT DEPLOYED"
fi

# Check S3 buckets
echo -e "\n🪣 S3 Buckets:"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

for bucket in articles faiss-backup; do
    if aws s3 ls s3://${ENVIRONMENT_NAME}-${bucket}-${ACCOUNT_ID} 2>/dev/null; then
        echo "  ✅ ${bucket}: exists"
    else
        echo "  ❌ ${bucket}: not found"
    fi
done

# Check EFS
echo -e "\n📁 EFS File System:"
EFS_ID=$(aws cloudformation describe-stacks \
    --stack-name ${ENVIRONMENT_NAME}-storage \
    --query 'Stacks[0].Outputs[?OutputKey==`FAISSFileSystemId`].OutputValue' \
    --output text \
    --region ${AWS_REGION} 2>/dev/null || echo "NOT_FOUND")

if [ "$EFS_ID" != "NOT_FOUND" ] && [ -n "$EFS_ID" ]; then
    EFS_STATUS=$(aws efs describe-file-systems \
        --file-system-id ${EFS_ID} \
        --query 'FileSystems[0].LifeCycleState' \
        --output text \
        --region ${AWS_REGION})
    echo "  ✅ Status: ${EFS_STATUS}"
    echo "  📍 ID: ${EFS_ID}"
else
    echo "  ❌ NOT DEPLOYED"
fi

echo -e "\n========================================="
echo "Status check complete!"
echo "========================================="
