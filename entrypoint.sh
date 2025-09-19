#!/bin/bash
set -e

# This script runs as root to fix volume permissions, then drops privileges

# Fix volume permissions if needed
if [ -d "/data" ]; then
    current_owner=$(stat -c %U /data 2>/dev/null || echo "unknown")
    if [ "$current_owner" != "app" ]; then
        echo "Fixing /data directory permissions (current owner: $current_owner)..."
        chown -R app:app /data
        echo "Permissions fixed successfully"
    else
        echo "/data permissions already correct (owner: app)"
    fi
else
    echo "/data directory not found, skipping permission fix"
fi

# Drop privileges and execute the main command as the app user
echo "Starting application as app user..."
exec gosu app "$@"