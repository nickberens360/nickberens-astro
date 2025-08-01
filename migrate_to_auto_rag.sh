#!/bin/bash
# migrate_to_auto_rag.sh - One-click migration script

set -e

echo "🚀 Starting Auto-Discovery RAG Migration..."

# Create backup of current system
echo "📦 Creating backup..."
mkdir -p backups/$(date +%Y%m%d_%H%M%S)
cp -r backend/ backups/$(date +%Y%m%d_%H%M%S)/ 2>/dev/null || true

# Install new dependencies
echo "📥 Installing LlamaIndex dependencies..."
pip install llama-index==0.9.48 llama-index-llms-anthropic==0.1.8 llama-index-embeddings-huggingface==0.1.6

# Optional: Install OCR support for images
read -p "Install OCR support for image processing? (y/N): " install_ocr
if [[ $install_ocr =~ ^[Yy]$ ]]; then
    echo "📸 Installing OCR support..."
    pip install pytesseract pillow

    # Try to install tesseract system dependency
    if command -v apt-get &> /dev/null; then
        sudo apt-get install -y tesseract-ocr
    elif command -v brew &> /dev/null; then
        brew install tesseract
    else
        echo "⚠️  Please install tesseract manually for your system"
    fi
fi

# Clean up old files (with confirmation)
echo "🧹 Cleaning up old system files..."
read -p "Remove old data_loader.py and build scripts? (y/N): " cleanup
if [[ $cleanup =~ ^[Yy]$ ]]; then
    rm -f backend/core/data_loader.py
    rm -f backend/scripts/build_unified_data.py
    rm -f public/unified_data.json
    echo "✅ Old files removed"
fi

# Create cache directory
mkdir -p .rag_cache

# Test the installation
echo "🧪 Testing new system..."
python -c "
try:
    from llama_index import VectorStoreIndex, SimpleDirectoryReader
    from llama_index.llms import Anthropic
    print('✅ LlamaIndex imports successful')
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
"

# Check if public directory has files
file_count=$(find public/ -type f 2>/dev/null | wc -l)
echo "📁 Found $file_count files in public/ directory"

if [ $file_count -eq 0 ]; then
    echo "⚠️  No files found in public/ directory"
    echo "Add some documents to test the auto-discovery system!"
fi

echo "
🎉 Migration Complete!

Next steps:
1. Update your main.py with the new integration code
2. Set your ANTHROPIC_API_KEY environment variable
3. Start your server: python -m backend.main
4. Test with: curl -X POST 'http://localhost:8000/query' -H 'Content-Type: application/json' -d '{\"question\": \"test\"}'

The system will now automatically discover and process any files you add to public/!
"

# Optional: Start the server
read -p "Start the server now? (y/N): " start_server
if [[ $start_server =~ ^[Yy]$ ]]; then
    echo "🚀 Starting server..."
    python -m backend.main
fi