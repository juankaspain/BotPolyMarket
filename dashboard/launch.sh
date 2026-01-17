#!/bin/bash
# v4.0 Dashboard Launcher

echo "🚀 Launching BotPolyMarket Enterprise Dashboard v4.0..."

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Instalar dependencias si es necesario
if ! python -c "import streamlit" 2>/dev/null; then
    echo "📦 Installing Streamlit..."
    pip install streamlit plotly pandas
fi

# Lanzar dashboard
echo "✅ Starting dashboard on http://localhost:8501"
streamlit run dashboard/streamlit_app.py \
    --server.port 8501 \
    --server.address localhost \
    --theme.base dark \
    --theme.primaryColor "#00ff00" \
    --theme.backgroundColor "#0e1117" \
    --theme.secondaryBackgroundColor "#1e1e1e"
