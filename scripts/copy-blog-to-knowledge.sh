#!/bin/bash

# Exit immediately if any command fails
set -e

# Create the backend/knowledge directory if it doesn't exist
mkdir -p backend/knowledge

# Copy all markdown files from src/content/blog to backend/knowledge
echo "Copying blog posts to backend/knowledge directory..."

if [ -d "src/content/blog" ]; then
    # Find and copy all .md and .mdx files
    find src/content/blog -type f \( -name "*.md" -o -name "*.mdx" \) -exec cp {} backend/knowledge/ \;
    
    # Count the files copied
    count=$(find src/content/blog -type f \( -name "*.md" -o -name "*.mdx" \) | wc -l)
    echo "✓ Copied $count blog post(s) to backend/knowledge"
else
    echo "⚠ Directory src/content/blog not found"
fi