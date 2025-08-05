#!/bin/bash
# Script to run cache preloading inside the backend container

# Check if container is running
if ! podman ps --format "{{.Names}}" | grep -q "^nickberens$"; then
    echo "❌ Backend container is not running. Please start it first with:"
    echo "   npm run backend:dev"
    exit 1
fi

# Run the preload script inside the container
echo "🚀 Running cache preload inside backend container..."
podman exec nickberens python /app/backend/scripts/preload_cache.py "$@"