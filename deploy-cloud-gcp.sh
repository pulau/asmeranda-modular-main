#!/bin/bash

# Google Cloud Platform Deployment Script for Asmeranda Modular Application
# This script deploys the application to GCP using Cloud Run

echo "🚀 Starting GCP Cloud Deployment for Asmeranda Modular Application"

# Check gcloud CLI is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Google Cloud SDK is not installed. Please install gcloud CLI first."
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format=value &> /dev/null; then
    echo "❌ Not authenticated with Google Cloud. Please run 'gcloud auth login'"
    exit 1
fi

# Variables
PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
BACKEND_SERVICE_NAME="asmeranda-backend"
FRONTEND_SERVICE_NAME="asmeranda-frontend"

echo "📦 Deploying to project: $PROJECT_ID in region: $REGION"

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com

# Configure Docker authentication
echo "🔐 Configuring Docker authentication..."
gcloud auth configure-docker $REGION-docker.pkg.dev

# Build and push backend image
echo "🔨 Building backend image..."
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/$BACKEND_SERVICE_NAME/backend:latest ./backend

# Build and push frontend image
echo "🔨 Building frontend image..."
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/$FRONTEND_SERVICE_NAME/frontend:latest ./frontend

# Deploy backend to Cloud Run
echo "🚀 Deploying backend to Cloud Run..."
gcloud run deploy $BACKEND_SERVICE_NAME \
    --image $REGION-docker.pkg.dev/$PROJECT_ID/$BACKEND_SERVICE_NAME/backend:latest \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --port 8000 \
    --memory 2Gi \
    --cpu 2

# Get backend URL
BACKEND_URL=$(gcloud run services describe $BACKEND_SERVICE_NAME --region $REGION --format 'value(status.url)')

# Deploy frontend to Cloud Run
echo "🚀 Deploying frontend to Cloud Run..."
gcloud run deploy $FRONTEND_SERVICE_NAME \
    --image $REGION-docker.pkg.dev/$PROJECT_ID/$FRONTEND_SERVICE_NAME/frontend:latest \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --port 3000 \
    --set-env-vars NEXT_PUBLIC_API_BASE_PATH=$BACKEND_URL/api/v1 \
    --memory 1Gi \
    --cpu 1

# Get frontend URL
FRONTEND_URL=$(gcloud run services describe $FRONTEND_SERVICE_NAME --region $REGION --format 'value(status.url)')

echo "✅ GCP Deployment completed!"
echo "🌐 Frontend URL: $FRONTEND_URL"
echo "🔧 Backend URL: $BACKEND_URL"
echo "📊 Monitor services: gcloud run services list --region $REGION"