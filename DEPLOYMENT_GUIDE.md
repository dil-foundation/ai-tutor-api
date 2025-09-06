# AI Tutor API - AWS ECS Fargate Deployment Guide

This guide provides step-by-step instructions for setting up and deploying the AI Tutor API to AWS ECS Fargate using the provided GitHub workflows.

## Prerequisites

### 1. AWS Account Setup
- AWS Account with appropriate permissions
- AWS CLI configured locally
- Docker installed locally (for testing)

### 2. Required AWS Resources

#### ECR Repository
```bash
aws ecr create-repository --repository-name ai-tutor-api --region us-east-1
```

#### ECS Cluster
```bash
aws ecs create-cluster --cluster-name ai-tutor-cluster --region us-east-1
```

#### CloudWatch Log Group
```bash
aws logs create-log-group --log-group-name /ecs/ai-tutor-backend --region us-east-1
```

#### IAM Roles

**ECS Task Execution Role:**
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
                "ecr:BatchGetImage"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:us-east-1:YOUR_ACCOUNT_ID:log-group:/ecs/ai-tutor-backend:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "arn:aws:secretsmanager:us-east-1:YOUR_ACCOUNT_ID:secret:ai-tutor/*"
        }
    ]
}
```

**ECS Task Role:**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "arn:aws:secretsmanager:us-east-1:YOUR_ACCOUNT_ID:secret:ai-tutor/*"
        }
    ]
}
```

### 3. GitHub Repository Setup

#### Required Secrets
Add the following secrets to your GitHub repository:

1. Go to Repository Settings → Secrets and variables → Actions
2. Add the following secrets:
   - `AWS_ACCESS_KEY_ID`: Your AWS access key
   - `AWS_SECRET_ACCESS_KEY`: Your AWS secret key

#### Required Environment Variables
Update the environment variables in the workflow files if needed:
- `AWS_REGION`: Your AWS region (default: us-east-1)
- `ECR_REPOSITORY`: ECR repository name (default: ai-tutor-api)
- `ECS_CLUSTER`: ECS cluster name (default: ai-tutor-cluster)
- `ECS_SERVICE`: ECS service name (default: ai-tutor-service)
- `ECS_TASK_DEFINITION`: ECS task definition name (default: ai-tutor-task-definition)

## Deployment Steps

### 1. Initial Setup

#### Create Task Definition
1. Update `ecs-task-definition.json` with your AWS account ID
2. Update secret ARNs to match your AWS Secrets Manager setup
3. Register the task definition:
```bash
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json
```

#### Create ECS Service
```bash
aws ecs create-service \
  --cluster ai-tutor-cluster \
  --service-name ai-tutor-service \
  --task-definition ai-tutor-task-definition \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-12345],securityGroups=[sg-12345],assignPublicIp=ENABLED}"
```

### 2. Configure Secrets

Store your application secrets in AWS Secrets Manager:

```bash
# OpenAI API Key
aws secretsmanager create-secret \
  --name ai-tutor/openai-api-key \
  --secret-string "your-openai-api-key"

# Database credentials
aws secretsmanager create-secret \
  --name ai-tutor/db-host \
  --secret-string "your-db-host"

aws secretsmanager create-secret \
  --name ai-tutor/db-name \
  --secret-string "your-db-name"

aws secretsmanager create-secret \
  --name ai-tutor/db-user \
  --secret-string "your-db-user"

aws secretsmanager create-secret \
  --name ai-tutor/db-password \
  --secret-string "your-db-password"

# ElevenLabs API Key
aws secretsmanager create-secret \
  --name ai-tutor/eleven-api-key \
  --secret-string "your-eleven-api-key"

# Supabase credentials
aws secretsmanager create-secret \
  --name ai-tutor/supabase-url \
  --secret-string "your-supabase-url"

aws secretsmanager create-secret \
  --name ai-tutor/supabase-service-key \
  --secret-string "your-supabase-service-key"
```

### 3. Deploy Using GitHub Actions

#### Automatic Deployment
1. Push code to the `main` branch
2. The CI/CD pipeline will automatically:
   - Run tests and linting
   - Build Docker image
   - Push to ECR
   - Deploy to ECS Fargate

#### Manual Deployment
1. Go to Actions tab in GitHub
2. Select "Deploy to ECS Fargate" workflow
3. Click "Run workflow"
4. Optionally specify image tag

### 4. Verify Deployment

#### Check ECS Service Status
```bash
aws ecs describe-services \
  --cluster ai-tutor-cluster \
  --services ai-tutor-service
```

#### Check Application Logs
```bash
aws logs tail /ecs/ai-tutor-backend --follow
```

#### Test Application Health
```bash
# Get the public IP or load balancer DNS
curl http://YOUR_PUBLIC_IP:8000/health
```

## Monitoring and Maintenance

### 1. CloudWatch Monitoring
- Set up CloudWatch alarms for CPU, memory, and error rates
- Monitor application logs for errors
- Set up log retention policies

### 2. Scaling
- Configure auto-scaling based on CPU/memory usage
- Set up Application Load Balancer for high availability
- Consider using ECS Service Discovery for service-to-service communication

### 3. Security
- Regularly rotate secrets
- Update base images for security patches
- Use VPC endpoints for ECR and ECS API calls
- Enable VPC Flow Logs for network monitoring

## Troubleshooting

### Common Issues

1. **Task Fails to Start**
   - Check task definition for syntax errors
   - Verify all secrets exist in Secrets Manager
   - Check IAM role permissions

2. **Service Unstable**
   - Check application health endpoint
   - Review CloudWatch logs
   - Verify environment variables

3. **Image Pull Errors**
   - Verify ECR repository exists
   - Check ECR permissions
   - Ensure image tag exists

4. **Deployment Timeout**
   - Check ECS service events
   - Verify load balancer health checks
   - Review security group rules

### Debug Commands

```bash
# Check ECS service events
aws ecs describe-services --cluster ai-tutor-cluster --services ai-tutor-service

# Check task definition
aws ecs describe-task-definition --task-definition ai-tutor-task-definition

# Check running tasks
aws ecs list-tasks --cluster ai-tutor-cluster --service-name ai-tutor-service

# Get task details
aws ecs describe-tasks --cluster ai-tutor-cluster --tasks TASK_ARN
```

## Cost Optimization

1. **Right-size Resources**: Start with minimal CPU/memory and scale up
2. **Use Spot Instances**: For non-critical workloads
3. **Implement Auto-scaling**: Scale down during low usage
4. **Monitor Costs**: Use AWS Cost Explorer and Budgets
5. **Clean Up**: Remove unused ECR images and old task definitions

## Security Best Practices

1. **Secrets Management**: Use AWS Secrets Manager for all sensitive data
2. **Network Security**: Use private subnets and security groups
3. **IAM Permissions**: Follow principle of least privilege
4. **Image Security**: Scan images for vulnerabilities
5. **Logging**: Enable comprehensive logging and monitoring

## Support

For issues or questions:
1. Check GitHub Actions logs
2. Review CloudWatch logs
3. Verify AWS resource configuration
4. Contact the development team
