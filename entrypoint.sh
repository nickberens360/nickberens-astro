#!/bin/sh
set -e

# This script runs as root to fix volume permissions, then drops privileges

# Fix volume permissions if needed
if [ -d "/data" ]; then
    # Validate that /data is actually a mount point for security
    if mountpoint -q /data; then
        echo "/data is a valid mount point, checking permissions..."
        current_owner=$(stat -c %U /data)
        if [ "$current_owner" != "app" ]; then
            echo "Fixing /data directory permissions (current owner: $current_owner)..."
            chown -R app:app /data
            echo "Permissions fixed successfully"
        else
            echo "/data permissions already correct (owner: app)"
        fi
    else
        echo "Warning: /data exists but is not a mount point, skipping permission fix"
    fi
else
    echo "/data directory not found, skipping permission fix"
fi

# Drop privileges and execute the main command as the app user
echo "Starting application as app user..."

# If no arguments provided, start the default uvicorn server
if [ $# -eq 0 ]; then
    set -- uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
fi

exec gosu app "$@"