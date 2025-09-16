#!/bin/bash

# Cloud Run Deployment Script for RAG Model Application
# Make sure you have gcloud CLI installed and configured

set -e

# Configuration
PROJECT_ID=${PROJECT_ID:-"your-gcp-project-id"}
REGION=${REGION:-"asia-northeast3"}  # Seoul region
BACKEND_SERVICE_NAME="rag-backend"
FRONTEND_SERVICE_NAME="rag-frontend"
OPENSEARCH_SERVICE_NAME="rag-opensearch"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Cloud Run deployment for RAG Model Application${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n 1 > /dev/null; then
    echo -e "${YELLOW}⚠️  Please authenticate with gcloud first:${NC}"
    echo "gcloud auth login"
    exit 1
fi

# Set project
echo -e "${YELLOW}📝 Setting GCP project to: ${PROJECT_ID}${NC}"
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo -e "${YELLOW}🔧 Enabling required APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com

# Create Artifact Registry repository if it doesn't exist
echo -e "${YELLOW}📦 Creating Artifact Registry repository...${NC}"
gcloud artifacts repositories create rag-repo \
    --repository-format=docker \
    --location=${REGION} \
    --description="RAG Model Application" || true

# Configure Docker authentication
echo -e "${YELLOW}🔐 Configuring Docker authentication...${NC}"
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Build and push backend
echo -e "${GREEN}🏗️  Building and deploying backend service...${NC}"
cd backend
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/rag-repo/${BACKEND_SERVICE_NAME}:latest

# Deploy backend to Cloud Run
echo -e "${YELLOW}🚀 Deploying backend to Cloud Run...${NC}"
gcloud run deploy ${BACKEND_SERVICE_NAME} \
    --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/rag-repo/${BACKEND_SERVICE_NAME}:latest \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --concurrency 80 \
    --max-instances 10 \
    --port 8000 \
    --set-env-vars "ENVIRONMENT=production" \
    --set-env-vars "OPENSEARCH_HOST=opensearch-service" \
    --set-env-vars "OPENSEARCH_PORT=9200" \
    --set-env-vars "OPENSEARCH_USER=admin" \
    --timeout 300

# Get backend URL
BACKEND_URL=$(gcloud run services describe ${BACKEND_SERVICE_NAME} --region=${REGION} --format="value(status.url)")
echo -e "${GREEN}✅ Backend deployed at: ${BACKEND_URL}${NC}"

# Build and push frontend
echo -e "${GREEN}🏗️  Building and deploying frontend service...${NC}"
cd ../frontend

# Update frontend environment for production
cat > .env.production << EOF
REACT_APP_API_URL=${BACKEND_URL}
GENERATE_SOURCEMAP=false
EOF

gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/rag-repo/${FRONTEND_SERVICE_NAME}:latest

# Deploy frontend to Cloud Run
echo -e "${YELLOW}🚀 Deploying frontend to Cloud Run...${NC}"
gcloud run deploy ${FRONTEND_SERVICE_NAME} \
    --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/rag-repo/${FRONTEND_SERVICE_NAME}:latest \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --concurrency 100 \
    --max-instances 5 \
    --port 3000 \
    --set-env-vars "ENVIRONMENT=production" \
    --set-env-vars "REACT_APP_API_URL=${BACKEND_URL}" \
    --timeout 300

# Get frontend URL
FRONTEND_URL=$(gcloud run services describe ${FRONTEND_SERVICE_NAME} --region=${REGION} --format="value(status.url)")
echo -e "${GREEN}✅ Frontend deployed at: ${FRONTEND_URL}${NC}"

cd ..

echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo ""
echo -e "${YELLOW}📋 Deployment Summary:${NC}"
echo -e "Backend URL:  ${BACKEND_URL}"
echo -e "Frontend URL: ${FRONTEND_URL}"
echo ""
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo "1. Set up OpenSearch service (consider using Elasticsearch on GCP)"
echo "2. Configure environment variables:"
echo "   - OPENAI_API_KEY"
echo "   - OPENSEARCH_HOST"
echo "   - OPENSEARCH_PASSWORD"
echo "3. Test the application"
echo ""
echo -e "${YELLOW}🔧 To update environment variables:${NC}"
echo "gcloud run services update ${BACKEND_SERVICE_NAME} --region=${REGION} --set-env-vars OPENAI_API_KEY=your-api-key"
echo ""
echo -e "${GREEN}✨ Happy coding!${NC}"