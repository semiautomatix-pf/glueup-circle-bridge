#!/bin/bash
# Quick setup script for GlueUp Circle Bridge UI

set -e

# Get the project root directory (parent of scripts/)
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🔄 Setting up GlueUp Circle Bridge Web UI..."
echo "📁 Project root: $PROJECT_ROOT"
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Found Python $python_version"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install backend dependencies
if [ -f "requirements.txt" ]; then
    echo "📦 Installing backend dependencies..."
    pip install -q -r requirements.txt
else
    echo "⚠️  requirements.txt not found, skipping backend dependencies"
fi

# Install UI dependencies
if [ -f "requirements-ui.txt" ]; then
    echo "📦 Installing UI dependencies..."
    pip install -q -r requirements-ui.txt
else
    echo "⚠️  requirements-ui.txt not found, skipping UI dependencies"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the application:"
echo ""
echo "  Quick start:"
echo "    ./scripts/start.sh"
echo ""
echo "  Or manually (two terminals):"
echo ""
echo "  Terminal 1 (Backend):"
echo "    source .venv/bin/activate"
echo "    python -m src.web.server"
echo ""
echo "  Terminal 2 (UI):"
echo "    source .venv/bin/activate"
echo "    streamlit run streamlit_app.py"
echo ""
