#!/bin/bash
# Start both backend and frontend for GlueUp Circle Bridge

set -e

# Cleanup function to kill child processes
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ -n "$STREAMLIT_PID" ]; then
        kill $STREAMLIT_PID 2>/dev/null || true
    fi
    # Give processes time to stop gracefully
    sleep 1
    # Force kill if still running
    if [ -n "$BACKEND_PID" ] && ps -p $BACKEND_PID > /dev/null 2>&1; then
        kill -9 $BACKEND_PID 2>/dev/null || true
    fi
    if [ -n "$STREAMLIT_PID" ] && ps -p $STREAMLIT_PID > /dev/null 2>&1; then
        kill -9 $STREAMLIT_PID 2>/dev/null || true
    fi
    echo "✅ Services stopped"
    exit 0
}

# Trap signals to ensure cleanup
trap cleanup SIGINT SIGTERM EXIT

# Get the project root directory (parent of scripts/)
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🚀 Starting GlueUp Circle Bridge..."
echo "📁 Project root: $PROJECT_ROOT"
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Run ./scripts/setup-ui.sh first"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Load .env file if it exists
if [ -f .env ]; then
    set -a  # automatically export all variables
    source .env
    set +a
fi

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit not installed. Run ./scripts/setup-ui.sh first"
    exit 1
fi

BACKEND_PORT="${SERVER_PORT:-8080}"
echo "🔧 Starting Flask backend on port $BACKEND_PORT..."
python -m src.web.server &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to be ready..."
for i in {1..10}; do
    if curl -s http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
        echo "✅ Backend is ready!"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "❌ Backend failed to start"
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

echo ""
echo "🌐 Starting Streamlit UI..."
streamlit run streamlit_app.py &
STREAMLIT_PID=$!

echo ""
echo "📊 Services running:"
echo "  - Flask backend: http://localhost:$BACKEND_PORT (PID: $BACKEND_PID)"
echo "  - Streamlit UI: http://localhost:8501 (PID: $STREAMLIT_PID)"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for Streamlit process to exit
wait $STREAMLIT_PID
