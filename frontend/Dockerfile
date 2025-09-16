# Multi-stage build for React frontend
FROM node:18-alpine as build

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (including dev dependencies for build)
RUN npm install

# Copy source code
COPY . .

# Build the app
RUN npm run build

# Production stage - use Node.js serve instead of nginx
FROM node:18-alpine

# Install serve globally
RUN npm install -g serve

# Set working directory
WORKDIR /app

# Copy built app from build stage
COPY --from=build /app/build ./build

# Expose port (Cloud Run will set PORT environment variable)
EXPOSE 8080

# Health check using PORT environment variable
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:${PORT:-8080}/ || exit 1

# Start serve on port from environment variable (Cloud Run requirement)
CMD sh -c "serve -s build -l ${PORT:-8080}"