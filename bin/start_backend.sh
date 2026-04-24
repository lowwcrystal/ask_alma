#!/bin/bash
# Start the FastAPI backend (Uvicorn)

echo "=================================="
echo "🚀 Starting AskAlma Backend API..."
echo "=================================="

# Navigate to project root (this script lives in bin/)
cd "$(dirname "$0")/.."

# Check if .env exists (project root preferred; backend/scripts/embedder/.env accepted for legacy setups)
if [ ! -f ".env" ] && [ ! -f "backend/scripts/embedder/.env" ]; then
    echo "⚠️  Warning: .env file not found at project root or backend/scripts/embedder/.env"
    echo "Please create one with OPENAI_API_KEY, DATABASE_URL, and (optionally) REDIS_URL"
    exit 1
fi

# Install/update Python dependencies
echo "📦 Installing Python dependencies..."
python3 -m pip install --user -q -r requirements.txt

echo "🎓 Starting FastAPI (Uvicorn) on http://localhost:5001"
echo ""
python3 -m backend.api.app
