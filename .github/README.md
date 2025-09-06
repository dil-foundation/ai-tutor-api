# GitHub Workflows for AI Tutor API

This directory contains GitHub Actions workflows for building, testing, and deploying the AI Tutor API to AWS ECS Fargate.

## Workflows Overview

### 1. Build and Push to ECR (`build-and-push-ecr.yml`)
- **Trigger**: Push to `main`/`develop` branches, pull requests, manual dispatch
- **Purpose**: Builds Docker image and pushes to AWS ECR
- **Features**:
  - Multi-platform Docker builds (linux/amd64)
  - Docker layer caching for faster builds
  - Automatic tagging based on branch and commit
  - Creates deployment artifacts for ECS deployment

### 2. Deploy to ECS Fargate (`deploy-ecs-fargate.yml`)
- **Trigger**: Completion of build workflow on `main` branch, manual dispatch
- **Purpose**: Deploys the containerized application to ECS Fargate
- **Features**:
  - Updates ECS task definition with new image
  - Forces new deployment in ECS service
  - Waits for deployment completion
  - Health checks and verification
  - Deployment summary reporting

### 3. Complete CI/CD Pipeline (`ci-cd-complete.yml`)
- **Trigger**: Push to `main`/`develop` branches, pull requests, manual dispatch
- **Purpose**: End-to-end CI/CD pipeline with testing, building, and deployment
- **Features**:
  - Python linting and testing
  - Docker image building and pushing
  - ECS Fargate deployment (main branch only)
  - Comprehensive error handling and reporting

## Prerequisites

### AWS Resources Required
1. **ECR Repository**: `ai-tutor-api`
2. **ECS Cluster**: `ai-tutor-cluster`
3. **ECS Service**: `ai-tutor-service`
4. **ECS Task Definition**: `ai-tutor-task-definition`
5. **Load Balancer**: For external access (optional but recommended)

### GitHub Secrets Required
Configure the following secrets in your GitHub repository:

```
AWS_ACCESS_KEY_ID          # AWS access key for ECR and ECS access
AWS_SECRET_ACCESS_KEY      # AWS secret key for ECR and ECS access
```

### AWS IAM Permissions
The AWS credentials need the following permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload",
                "ecr:PutImage"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ecs:DescribeTaskDefinition",
                "ecs:RegisterTaskDefinition",
                "ecs:UpdateService",
                "ecs:DescribeServices",
                "ecs:ListTasks"
            ],
            "Resource": "*"
        }
    ]
}
```

## Configuration

### Environment Variables
The workflows use the following environment variables (can be customized in workflow files):

```yaml
AWS_REGION: us-east-1
ECR_REPOSITORY: ai-tutor-api
ECS_CLUSTER: ai-tutor-cluster
ECS_SERVICE: ai-tutor-service
ECS_TASK_DEFINITION: ai-tutor-task-definition
ECS_CONTAINER_NAME: ai-tutor-backend
```

### Customization
To customize the workflows for your environment:

1. **Update environment variables** in the workflow files
2. **Modify AWS region** if different from `us-east-1`
3. **Update ECR repository name** if different
4. **Update ECS resource names** to match your infrastructure
5. **Add additional tests** in the CI/CD pipeline as needed

## Usage

### Automatic Deployment
- Push to `main` branch triggers full CI/CD pipeline
- Push to `develop` branch triggers build and test only
- Pull requests trigger build and test only

### Manual Deployment
1. Go to Actions tab in GitHub
2. Select "Deploy to ECS Fargate" workflow
3. Click "Run workflow"
4. Optionally specify image tag and force deployment

### Monitoring Deployments
- Check the Actions tab for workflow status
- View deployment summaries in workflow runs
- Monitor ECS service in AWS Console
- Check application logs in CloudWatch

## Troubleshooting

### Common Issues

1. **ECR Push Fails**
   - Verify AWS credentials are correct
   - Check ECR repository exists
   - Ensure IAM permissions include ECR access

2. **ECS Deployment Fails**
   - Verify ECS cluster and service exist
   - Check task definition is valid
   - Ensure container image exists in ECR

3. **Service Not Stable**
   - Check application health endpoints
   - Verify environment variables in task definition
   - Check CloudWatch logs for errors

### Debug Steps
1. Check workflow logs in GitHub Actions
2. Verify AWS resources exist and are accessible
3. Test Docker image locally before deployment
4. Check ECS service events in AWS Console

## Security Considerations

1. **Secrets Management**: Use GitHub Secrets for sensitive data
2. **IAM Permissions**: Follow principle of least privilege
3. **Image Security**: Regularly update base images
4. **Network Security**: Configure security groups appropriately
5. **Logging**: Enable CloudTrail for audit logging

## Support

For issues or questions:
1. Check workflow logs for error details
2. Verify AWS resource configuration
3. Review this documentation
4. Contact the development team
