#!/bin/bash
# Stop GlueUp Circle Bridge services

echo "🛑 Stopping GlueUp Circle Bridge services..."

# Find and kill Flask backend
FLASK_PID=$(pgrep -f "python -m src.web.server" || true)
if [ -n "$FLASK_PID" ]; then
    echo "  Stopping Flask backend (PID: $FLASK_PID)..."
    kill $FLASK_PID 2>/dev/null || true
    sleep 1
    # Force kill if still running
    if ps -p $FLASK_PID > /dev/null 2>&1; then
        kill -9 $FLASK_PID 2>/dev/null || true
    fi
    echo "  ✅ Flask stopped"
else
    echo "  ℹ️  Flask backend not running"
fi

# Find and kill Streamlit
STREAMLIT_PID=$(pgrep -f "streamlit run streamlit_app.py" || true)
if [ -n "$STREAMLIT_PID" ]; then
    echo "  Stopping Streamlit (PID: $STREAMLIT_PID)..."
    kill $STREAMLIT_PID 2>/dev/null || true
    sleep 1
    # Force kill if still running
    if ps -p $STREAMLIT_PID > /dev/null 2>&1; then
        kill -9 $STREAMLIT_PID 2>/dev/null || true
    fi
    echo "  ✅ Streamlit stopped"
else
    echo "  ℹ️  Streamlit not running"
fi

echo "✅ All services stopped"
