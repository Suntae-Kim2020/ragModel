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
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

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

# Expose port (Cloud Run will set PORT environment variable)
EXPOSE 8080

# Create a non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Run the application using PORT environment variable from Cloud Run
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]