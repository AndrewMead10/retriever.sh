#!/bin/bash

# Service Update Script
# This script updates the deployment with new changes (no Docker)
# Usage: ./update-deployment.sh

set -e

SERVICE_NAME="retriever"
SERVICE_PORT="5656"

echo "Updating ${SERVICE_NAME} Service deployment (no Docker)..."

# Check if running in the correct directory
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "Error: backend/ or frontend/ not found in current directory"
    echo "Please run this script from the project root directory"
    exit 1
fi

# Check if service exists
if ! systemctl is-enabled "$SERVICE_NAME" &> /dev/null; then
    echo "Service $SERVICE_NAME is not set up. Please run setup-service.sh first."
    exit 1
fi

echo "Stopping the service..."
sudo systemctl stop "$SERVICE_NAME"

echo "Pulling latest changes (if this is a git repository)..."
if [ -d ".git" ]; then
    git pull origin $(git branch --show-current) || echo "No git repository or failed to pull"
fi

echo "Building frontend into backend static assets..."
(
    cd frontend
    npm install
    npm run build
)

echo "Syncing backend dependencies and running migrations..."
(
    cd backend
    uv sync
    uv run alembic upgrade head
)

echo "Starting updated service..."
sudo systemctl start "$SERVICE_NAME"

echo "Checking service status..."
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "✅ Service is running successfully!"
    
    # Check if the API is responding
    if curl -s -f http://127.0.0.1:${SERVICE_PORT}/ > /dev/null; then
        echo "✅ API is responding at http://127.0.0.1:${SERVICE_PORT}"
    else
        echo "⚠️  Service is running but API may not be ready yet"
    fi
else
    echo "❌ Service failed to start"
    echo "Check service logs with: sudo systemctl status $SERVICE_NAME"
    exit 1
fi

echo ""
echo "Update complete!"
echo "Service logs: sudo journalctl -u $SERVICE_NAME -f"
