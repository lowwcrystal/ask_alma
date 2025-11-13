#!/bin/bash
# Start the Flask API backend

echo "=================================="
echo "🚀 Starting AskAlma Backend API..."
echo "=================================="

# Navigate to project root
cd "$(dirname "$0")"

# Check if .env exists (check both root and src/embedder locations)
if [ ! -f ".env" ] && [ ! -f "src/embedder/.env" ]; then
    echo "⚠️  Warning: .env file not found at project root or src/embedder/.env"
    echo "Please create it with your OPENAI_API_KEY and DATABASE_URL"
    exit 1
fi

# Install/update Python dependencies
echo "📦 Installing Python dependencies..."
python3 -m pip install --user -q -r requirements.txt

# Start the Flask server
echo "🎓 Starting Flask API server on http://localhost:5001"
echo ""
python3 api/app.py

