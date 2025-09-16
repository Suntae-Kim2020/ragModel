# Cloud Run Deployment Guide

This guide explains how to deploy the RAG Model Application to Google Cloud Run.

## Prerequisites

1. **Google Cloud Account**: You need a GCP account with billing enabled
2. **gcloud CLI**: Install the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install)
3. **Docker**: Install [Docker](https://docs.docker.com/get-docker/) on your local machine
4. **Project Setup**: Create a new GCP project or use an existing one

## Setup Instructions

### 1. Configure Google Cloud

```bash
# Authenticate with Google Cloud
gcloud auth login

# Set your project ID
export PROJECT_ID="your-gcp-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

### 2. Configure Environment Variables

```bash
# Copy the environment template
cp .env.cloudrun .env.production

# Edit the file with your actual values
nano .env.production
```

Required environment variables:
- `PROJECT_ID`: Your GCP project ID
- `OPENAI_API_KEY`: Your OpenAI API key
- `OPENSEARCH_HOST`: Your OpenSearch/Elasticsearch endpoint
- `OPENSEARCH_PASSWORD`: Your OpenSearch password

### 3. Deploy to Cloud Run

#### Option A: Automated Deployment (Recommended)

```bash
# Make the deployment script executable
chmod +x deploy-cloudrun.sh

# Run the deployment script
./deploy-cloudrun.sh
```

#### Option B: Manual Deployment

```bash
# Set variables
PROJECT_ID="your-gcp-project-id"
REGION="asia-northeast3"

# Build and deploy backend
cd backend
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/rag-repo/rag-backend:latest
gcloud run deploy rag-backend \
    --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/rag-repo/rag-backend:latest \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --port 8000

# Build and deploy frontend
cd ../frontend
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/rag-repo/rag-frontend:latest
gcloud run deploy rag-frontend \
    --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/rag-repo/rag-frontend:latest \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --port 3000
```

### 4. Configure Environment Variables

```bash
# Set OpenAI API key
gcloud run services update rag-backend \
    --region=asia-northeast3 \
    --set-env-vars OPENAI_API_KEY=your-actual-api-key

# Set OpenSearch configuration
gcloud run services update rag-backend \
    --region=asia-northeast3 \
    --set-env-vars OPENSEARCH_HOST=your-opensearch-endpoint,OPENSEARCH_PASSWORD=your-password
```

### 5. Set up OpenSearch

You have several options for OpenSearch:

#### Option A: Elastic Cloud (Recommended)
1. Create an account at [Elastic Cloud](https://cloud.elastic.co/)
2. Create a new Elasticsearch deployment
3. Use the endpoint and credentials in your environment variables

#### Option B: Self-hosted OpenSearch
1. Deploy OpenSearch on Google Compute Engine
2. Configure security and networking
3. Update your environment variables

#### Option C: Local Development Only
- For development, use the included docker-compose setup

## Post-Deployment Configuration

### 1. Test the Application

```bash
# Get the service URLs
BACKEND_URL=$(gcloud run services describe rag-backend --region=asia-northeast3 --format="value(status.url)")
FRONTEND_URL=$(gcloud run services describe rag-frontend --region=asia-northeast3 --format="value(status.url)")

echo "Backend: $BACKEND_URL"
echo "Frontend: $FRONTEND_URL"

# Test backend health
curl $BACKEND_URL/health

# Test frontend
curl $FRONTEND_URL/health
```

### 2. Configure Custom Domain (Optional)

```bash
# Map custom domain
gcloud run domain-mappings create \
    --service=rag-frontend \
    --domain=yourdomain.com \
    --region=asia-northeast3
```

### 3. Monitor and Scale

```bash
# View logs
gcloud run logs read rag-backend --region=asia-northeast3
gcloud run logs read rag-frontend --region=asia-northeast3

# Update scaling settings
gcloud run services update rag-backend \
    --region=asia-northeast3 \
    --max-instances=10 \
    --concurrency=80
```

## Cost Optimization

### 1. Set Resource Limits

```bash
# Optimize backend resources
gcloud run services update rag-backend \
    --region=asia-northeast3 \
    --memory=1Gi \
    --cpu=1 \
    --max-instances=5

# Optimize frontend resources
gcloud run services update rag-frontend \
    --region=asia-northeast3 \
    --memory=512Mi \
    --cpu=1 \
    --max-instances=3
```

### 2. Enable CPU Allocation

```bash
# Only allocate CPU during requests
gcloud run services update rag-backend \
    --region=asia-northeast3 \
    --cpu-allocation=request-only
```

## Troubleshooting

### Common Issues

1. **Build Failures**
   ```bash
   # Check build logs
   gcloud builds log [BUILD_ID]
   ```

2. **Service Not Starting**
   ```bash
   # Check service logs
   gcloud run logs read rag-backend --region=asia-northeast3
   ```

3. **Environment Variables**
   ```bash
   # List current environment variables
   gcloud run services describe rag-backend --region=asia-northeast3
   ```

### Performance Tuning

1. **Memory Optimization**
   - Monitor memory usage in Cloud Console
   - Adjust memory allocation based on usage patterns

2. **Cold Starts**
   - Consider keeping minimum instances > 0 for production
   - Optimize container startup time

3. **Concurrency**
   - Tune concurrency settings based on your workload
   - Monitor request latency and error rates

## Security Best Practices

1. **Environment Variables**
   - Use Secret Manager for sensitive data
   - Never commit secrets to version control

2. **Authentication**
   - Enable authentication for production environments
   - Use IAM for service-to-service communication

3. **Network Security**
   - Configure VPC and firewall rules appropriately
   - Use HTTPS for all external communications

## Backup and Recovery

1. **Regular Backups**
   - Back up your OpenSearch indices regularly
   - Export application configuration

2. **Disaster Recovery**
   - Document your deployment process
   - Test recovery procedures periodically

## Support

For deployment issues:
1. Check the [Cloud Run documentation](https://cloud.google.com/run/docs)
2. Review application logs in Cloud Console
3. Check this repository's Issues section

## Next Steps

After successful deployment:
1. Set up monitoring and alerting
2. Configure automated backups
3. Implement CI/CD pipeline
4. Set up staging environment
5. Configure custom domains and SSL