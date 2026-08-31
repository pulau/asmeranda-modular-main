FROM node:18-alpine

WORKDIR /app

# Build arguments with defaults for Docker environment
ARG DOCKER_MODE=true
ARG DOCKER_API_BASE=http://backend:8000
ARG NEXT_PUBLIC_API_BASE=http://backend:8000
ARG NEXT_PUBLIC_API_BASE_PATH=/api/v1

ENV DOCKER_MODE=${DOCKER_MODE}
ENV DOCKER_API_BASE=${DOCKER_API_BASE}
ENV NEXT_PUBLIC_API_BASE=${NEXT_PUBLIC_API_BASE}
ENV NEXT_PUBLIC_API_BASE_PATH=${NEXT_PUBLIC_API_BASE_PATH}

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy application code
COPY . .

# Build the application
RUN npm run build

# Expose port
EXPOSE 3000

# Start the application
CMD ["npm", "start"]