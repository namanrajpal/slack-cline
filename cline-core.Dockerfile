# Dockerfile for Cline Core - Compiles and runs in Linux
FROM node:18-alpine

# Install build dependencies
RUN apk add --no-cache python3 make g++ git

WORKDIR /app

# Copy Cline source code
COPY cline/package*.json ./
RUN npm install --production=false

COPY cline/ ./

# Compile Cline Core standalone build
RUN npm run compile-standalone

# Create directory for workspace data
RUN mkdir -p /workspaces

# Set default working directory for Cline
WORKDIR /workspaces

# Expose gRPC port
EXPOSE 50051

# Run Cline Core
CMD ["node", "/app/dist-standalone/cline-core.js", "--port", "50051", "--config", "/root/.cline"]
