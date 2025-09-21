#!/bin/bash

# Script to update ECS service with new image
# Usage: ./update-ecs-image.sh [image-tag] [environment]

set -e

# Default values
IMAGE_TAG=${1:-latest}
ENVIRONMENT=${2:-dev}
AWS_REGION="us-east-2"
ECR_REPOSITORY="ai-tutor-api"

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"

# ECS configuration based on environment
case $ENVIRONMENT in
  "dev")
    CLUSTER_NAME="dil-fnd-ecs-cluster"
    SERVICE_NAME="dil-fnd-task-definition"
    ;;
  "staging")
    CLUSTER_NAME="dil-fnd-ecs-cluster-staging"
    SERVICE_NAME="dil-fnd-task-definition-staging"
    ;;
  "prod")
    CLUSTER_NAME="dil-fnd-ecs-cluster-prod"
    SERVICE_NAME="dil-fnd-task-definition-prod"
    ;;
  *)
    echo "Invalid environment. Use: dev, staging, or prod"
    exit 1
    ;;
esac

echo "🚀 Updating ECS service with new image..."
echo "Environment: $ENVIRONMENT"
echo "Image: $ECR_URI:$IMAGE_TAG"
echo "Cluster: $CLUSTER_NAME"
echo "Service: $SERVICE_NAME"

# Check if image exists in ECR
echo "🔍 Checking if image exists in ECR..."
if ! aws ecr describe-images --repository-name $ECR_REPOSITORY --image-ids imageTag=$IMAGE_TAG --region $AWS_REGION > /dev/null 2>&1; then
    echo "❌ Image $ECR_URI:$IMAGE_TAG not found in ECR"
    echo "Available tags:"
    aws ecr list-images --repository-name $ECR_REPOSITORY --region $AWS_REGION --query 'imageIds[].imageTag' --output table
    exit 1
fi

echo "✅ Image found in ECR"

# Get the current task definition
echo "📋 Getting current task definition..."
TASK_DEFINITION=$(aws ecs describe-task-definition --task-definition $SERVICE_NAME --query 'taskDefinition')

# Update the image URI in the task definition
echo "🔄 Updating task definition with new image..."
UPDATED_TASK_DEFINITION=$(echo $TASK_DEFINITION | jq --arg IMAGE_URI "$ECR_URI:$IMAGE_TAG" '.containerDefinitions[0].image = $IMAGE_URI')

# Remove fields that shouldn't be in the new task definition
UPDATED_TASK_DEFINITION=$(echo $UPDATED_TASK_DEFINITION | jq 'del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .placementConstraints, .compatibilities, .registeredAt, .registeredBy)')

# Register the new task definition
echo "📝 Registering new task definition..."
NEW_TASK_DEFINITION=$(aws ecs register-task-definition --cli-input-json "$UPDATED_TASK_DEFINITION" --query 'taskDefinition.taskDefinitionArn' --output text)

echo "✅ New task definition registered: $NEW_TASK_DEFINITION"

# Update the service with the new task definition
echo "🚀 Updating ECS service..."
aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service $SERVICE_NAME \
    --task-definition $NEW_TASK_DEFINITION \
    --force-new-deployment

echo "✅ ECS service update initiated"

# Wait for deployment to complete
echo "⏳ Waiting for deployment to complete..."
aws ecs wait services-stable \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME

echo "🎉 Deployment completed successfully!"

# Get final service status
echo "📊 Final service status:"
aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --query 'services[0].{ServiceName:serviceName,Status:status,RunningCount:runningCount,PendingCount:pendingCount,DesiredCount:desiredCount,TaskDefinition:taskDefinition}'
