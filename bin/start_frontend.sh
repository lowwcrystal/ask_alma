#!/bin/bash
# Start the React frontend

echo "=================================="
echo "🎨 Starting AskAlma Frontend..."
echo "=================================="

# Navigate to frontend directory (this script lives in bin/)
cd "$(dirname "$0")/../frontend"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing npm dependencies (first time)..."
    npm install
fi

# Start the React development server
echo "🚀 Starting React dev server on http://localhost:3000"
echo ""
npm start

