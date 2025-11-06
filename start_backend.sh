#!/bin/bash
# Start the Flask API backend

echo "=================================="
echo "🚀 Starting AskAlma Backend API..."
echo "=================================="

# Navigate to project root
cd "$(dirname "$0")"

# Check if .env exists
if [ ! -f "src/embedder/.env" ]; then
    echo "⚠️  Warning: .env file not found at src/embedder/.env"
    echo "Please create it with your OPENAI_API_KEY and DATABASE_URL"
    exit 1
fi

# Install/update Python dependencies
echo "📦 Installing Python dependencies..."
python3 -m pip install --user -q -r requirements.txt

# Start the Flask server
echo "🎓 Starting Flask API server on http://localhost:5000"
echo ""
python3 backend/api.py

