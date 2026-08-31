#!/bin/bash

# AWS Cloud Deployment Script for Asmeranda Modular Application
# This script deploys the application to AWS using Elastic Beanstalk

echo "🚀 Starting AWS Cloud Deployment for Asmeranda Modular Application"

# Check AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install AWS CLI first."
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Please run 'aws configure'"
    exit 1
fi

# Variables
APP_NAME="asmeranda-modular"
S3_BUCKET="asmeranda-deployment-$(aws sts get-caller-identity --query Account --output text)"
REGION="us-east-1"

echo "📦 Creating S3 bucket for deployment..."
aws s3 mb s3://$S3_BUCKET --region $REGION 2>/dev/null || echo "Bucket may already exist"

echo "🔨 Building Docker images..."
docker build -t $APP_NAME-backend ./backend
docker build -t $APP_NAME-frontend ./frontend

echo "🏷️ Tagging images for ECR..."
docker tag $APP_NAME-backend:latest $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$APP_NAME-backend:latest
docker tag $APP_NAME-frontend:latest $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$APP_NAME-frontend:latest

echo "📤 Pushing images to ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
docker push $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$APP_NAME-backend:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$APP_NAME-frontend:latest

echo "🚀 Deploying to Elastic Beanstalk..."
# Create application if it doesn't exist
aws elasticbeanstalk create-application --application-name $APP_NAME --region $REGION 2>/dev/null || echo "Application may already exist"

# Create application version
aws elasticbeanstalk create-application-version \
    --application-name $APP_NAME \
    --version-label "v1.0.0" \
    --source-bundle S3Bucket=$S3_BUCKET,S3Key=dockerrun.aws.json \
    --region $REGION

# Create environment
aws elasticbeanstalk create-environment \
    --application-name $APP_NAME \
    --environment-name "asmeranda-production" \
    --version-label "v1.0.0" \
    --solution-stack-name "64bit Amazon Linux 2 v5.8.0 running Docker" \
    --option-settings Namespace=aws:elasticbeanstalk:container:docker,OptionName=Image,Value=$AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$APP_NAME-backend:latest \
    --region $REGION

echo "✅ AWS Deployment completed!"
echo "🌐 Application URL: http://asmeranda-production.elasticbeanstalk.com"
echo "📊 Monitor deployment: aws elasticbeanstalk describe-environment-events --environment-name asmeranda-production --region $REGION"