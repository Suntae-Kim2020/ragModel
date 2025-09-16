# Use Python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.minimal.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.minimal.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Set default environment variables for Cloud Run
ENV OPENAI_API_KEY=${OPENAI_API_KEY:-""}
ENV OPENSEARCH_HOST=${OPENSEARCH_HOST:-"localhost"}
ENV OPENSEARCH_PORT=${OPENSEARCH_PORT:-"9200"}
ENV OPENSEARCH_USERNAME=${OPENSEARCH_USERNAME:-"admin"}
ENV OPENSEARCH_PASSWORD=${OPENSEARCH_PASSWORD:-"admin"}

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application as root (Cloud Run handles security) - use simple version for testing
CMD ["uvicorn", "simple_main:app", "--host", "0.0.0.0", "--port", "8000"]