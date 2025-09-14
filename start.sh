#!/bin/bash

echo "Starting RAG Document Management System..."

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose is not installed"
    exit 1
fi

# Start OpenSearch services
echo "Starting OpenSearch services..."
docker-compose up -d

# Wait for OpenSearch to be ready
echo "Waiting for OpenSearch to be ready..."
sleep 30

# Check if OpenSearch is running
until curl -s http://localhost:9200 > /dev/null; do
    echo "Waiting for OpenSearch to start..."
    sleep 5
done

echo "OpenSearch is ready!"

# Create .env file if it doesn't exist
if [ ! -f backend/.env ]; then
    echo "Creating .env file..."
    cp backend/.env.example backend/.env
    echo "Please edit backend/.env and add your OpenAI API key"
fi

# Install Python dependencies
echo "Installing Python dependencies..."
cd backend
pip install -r requirements.txt

# Start FastAPI backend
echo "Starting FastAPI backend..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Go back to root directory
cd ..

# Install Node.js dependencies and start frontend
echo "Installing Node.js dependencies..."
cd frontend
npm install

echo "Starting React frontend..."
npm start &
FRONTEND_PID=$!

# Go back to root directory
cd ..

echo ""
echo "🎉 RAG Document Management System is starting!"
echo ""
echo "Services:"
echo "- OpenSearch: http://localhost:9200"
echo "- OpenSearch Dashboard: http://localhost:5601"
echo "- Backend API: http://localhost:8000"
echo "- Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    docker-compose down
    exit 0
}

# Trap Ctrl+C
trap cleanup SIGINT

# Wait for processes
wait