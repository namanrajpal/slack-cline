#!/bin/bash
# Quick setup script for slack-cline

set -e

echo "🚀 Setting up slack-cline..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your Slack credentials before running!"
fi

# Compile proto files if not already done
echo "🔧 Compiling proto files..."
if [ ! -d "backend/venv" ]; then
    echo "Creating Python virtual environment..."
    python -m venv backend/venv
fi

source backend/venv/bin/activate
pip install -q -r requirements.txt
cd backend && python compile_protos.py && cd ..

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your Slack credentials"
echo "2. Run: docker-compose build  (first time only, ~5-10 min)"
echo "3. Run: docker-compose up"
echo "4. Run: ngrok http 8000  (in another terminal)"
echo "5. Update Slack app URLs with ngrok URL"
echo ""
echo "Then test: /cline run create a readme file"
echo ""
