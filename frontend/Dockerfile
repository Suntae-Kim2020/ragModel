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

# Install serve globally and wget for health checks
RUN npm install -g serve && apk add --no-cache wget

# Set working directory
WORKDIR /app

# Copy built app from build stage
COPY --from=build /app/build ./build

# Create a non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nextjs -u 1001
RUN chown -R nextjs:nodejs /app
USER nextjs

# Expose port (Cloud Run will set PORT environment variable)
EXPOSE 8080

# Start serve on port from environment variable (Cloud Run requirement)
CMD serve -s build -p ${PORT:-8080} --host 0.0.0.0 --no-clipboard