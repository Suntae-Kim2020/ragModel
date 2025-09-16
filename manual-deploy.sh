#!/bin/bash

# Manual deployment script for RAG backend
set -e

# Configuration
PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project)}
REGION=${REGION:-"asia-northeast3"}
SERVICE_NAME="rag-backend"

echo "🚀 Starting manual deployment for RAG backend"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"

# Build and push backend manually
echo "📦 Building backend container..."
cd backend

# Create a simple Dockerfile if needed
cat > Dockerfile << 'EOF'
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

echo "🏗️ Building container image..."
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/rag-repo/$SERVICE_NAME:latest .

echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image $REGION-docker.pkg.dev/$PROJECT_ID/rag-repo/$SERVICE_NAME:latest \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --concurrency 80 \
    --max-instances 10 \
    --port 8000 \
    --set-env-vars "ENVIRONMENT=production" \
    --timeout 300

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")
echo "✅ Backend deployed successfully!"
echo "Service URL: $SERVICE_URL"

echo "🔍 Testing health endpoint..."
sleep 10
curl -f "$SERVICE_URL/health" || echo "Health check failed, but service might still be starting..."

cd ..
echo "✨ Deployment complete!"