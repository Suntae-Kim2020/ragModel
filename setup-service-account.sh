#!/bin/bash

# Service Account Setup Script for GitHub Actions
# This script creates a service account and generates a key for GitHub Actions

set -e

# Configuration
PROJECT_ID="ragp-472304"
SERVICE_ACCOUNT_NAME="github-actions-deploy"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
KEY_FILE="service-account-key.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔐 Setting up Service Account for GitHub Actions${NC}"

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Set project
echo -e "${YELLOW}📝 Setting GCP project to: ${PROJECT_ID}${NC}"
gcloud config set project ${PROJECT_ID}

# Create service account
echo -e "${YELLOW}👤 Creating service account: ${SERVICE_ACCOUNT_NAME}${NC}"
gcloud iam service-accounts create ${SERVICE_ACCOUNT_NAME} \
    --display-name="GitHub Actions Deploy Service Account" \
    --description="Service account for GitHub Actions CI/CD deployment" || true

# Grant necessary roles
echo -e "${YELLOW}🔑 Granting roles to service account...${NC}"

# Cloud Run Admin
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/run.admin"

# Cloud Build Editor
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/cloudbuild.builds.editor"

# Artifact Registry Writer
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/artifactregistry.writer"

# Storage Admin (for Cloud Build artifacts)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/storage.admin"

# Service Account User (to act as service accounts)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/iam.serviceAccountUser"

# Service Usage Consumer
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/serviceusage.serviceUsageConsumer"

# Create and download service account key
echo -e "${YELLOW}🗝️  Creating service account key...${NC}"
gcloud iam service-accounts keys create ${KEY_FILE} \
    --iam-account=${SERVICE_ACCOUNT_EMAIL}

echo -e "${GREEN}✅ Service account setup completed!${NC}"
echo ""
echo -e "${YELLOW}📋 Setup Summary:${NC}"
echo -e "Service Account: ${SERVICE_ACCOUNT_EMAIL}"
echo -e "Key File: ${KEY_FILE}"
echo ""
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo "1. Go to your GitHub repository: https://github.com/suntaekim/ragModel"
echo "2. Go to Settings > Secrets and variables > Actions"
echo "3. Add the following repository secrets:"
echo ""
echo -e "${GREEN}   Secret Name: GCP_SA_KEY${NC}"
echo "   Secret Value: Copy the entire content of ${KEY_FILE}"
echo ""
echo -e "${GREEN}   Secret Name: OPENAI_API_KEY${NC}"
echo "   Secret Value: Your OpenAI API key"
echo ""
echo -e "${YELLOW}📖 To view the service account key content:${NC}"
echo "cat ${KEY_FILE}"
echo ""
echo -e "${RED}⚠️  SECURITY WARNING:${NC}"
echo "- Keep the ${KEY_FILE} file secure and never commit it to your repository"
echo "- Consider deleting the key file after adding it to GitHub secrets"
echo "- You can regenerate keys if needed using the GCP Console"
echo ""
echo -e "${GREEN}✨ Ready for automated deployment!${NC}"