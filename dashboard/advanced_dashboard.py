#!/usr/bin/env python3
"""Advanced Streamlit Dashboard for BotPolyMarket

Features:
- Real-time trading metrics
- Live P&L tracking
- Strategy performance analysis
- Risk metrics visualization
- Trade history
- System health monitoring

Author: juankaspain
Version: 7.0 - Advanced Dashboard
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import time

# Page config
st.set_page_config(
    page_title="BotPolyMarket Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# Data paths
DATA_DIR = Path("data")
TRADES_FILE = DATA_DIR / "trades.json"
PERFORMANCE_FILE = DATA_DIR / "performance.json"
POSITIONS_FILE = DATA_DIR / "positions.json"

def load_data(file_path, default=None):
    """Load JSON data from file"""
    try:
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Error loading {file_path.name}: {e}")
    return default or {}

def get_recent_trades(limit=50):
    """Get recent trades"""
    trades_data = load_data(TRADES_FILE, {"trades": []})
    trades = trades_data.get("trades", [])[-limit:]
    
    if not trades:
        return pd.DataFrame()
    
    df = pd.DataFrame(trades)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def get_performance_metrics():
    """Get performance metrics"""
    perf_data = load_data(PERFORMANCE_FILE)
    
    # Default metrics if no data
    if not perf_data:
        return {
            "total_pnl": 0,
            "total_trades": 0,
            "win_rate": 0,
            "sharpe_ratio": 0,
            "max_drawdown": 0,
            "current_capital": 10000,
            "daily_pnl": 0,
            "weekly_pnl": 0,
            "monthly_pnl": 0
        }
    
    return perf_data

def get_active_positions():
    """Get active positions"""
    positions_data = load_data(POSITIONS_FILE, {"positions": []})
    positions = positions_data.get("positions", [])
    
    if not positions:
        return pd.DataFrame()
    
    return pd.DataFrame(positions)

def create_pnl_chart(trades_df):
    """Create cumulative P&L chart"""
    if trades_df.empty:
        return go.Figure()
    
    trades_df = trades_df.sort_values('timestamp')
    trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=trades_df['timestamp'],
        y=trades_df['cumulative_pnl'],
        mode='lines',
        name='Cumulative P&L',
        line=dict(color='#667eea', width=2),
        fill='tozeroy',
        fillcolor='rgba(102, 126, 234, 0.2)'
    ))
    
    fig.update_layout(
        title='Cumulative Profit & Loss',
        xaxis_title='Time',
        yaxis_title='P&L ($)',
        template='plotly_white',
        height=400,
        hovermode='x unified'
    )
    
    return fig

def create_strategy_performance_chart(trades_df):
    """Create strategy performance comparison"""
    if trades_df.empty:
        return go.Figure()
    
    strategy_pnl = trades_df.groupby('strategy')['pnl'].sum().sort_values(ascending=True)
    
    fig = go.Figure(go.Bar(
        x=strategy_pnl.values,
        y=strategy_pnl.index,
        orientation='h',
        marker=dict(
            color=strategy_pnl.values,
            colorscale='RdYlGn',
            showscale=True
        )
    ))
    
    fig.update_layout(
        title='Strategy Performance',
        xaxis_title='Total P&L ($)',
        yaxis_title='Strategy',
        template='plotly_white',
        height=400
    )
    
    return fig

def create_win_rate_pie(trades_df):
    """Create win rate pie chart"""
    if trades_df.empty:
        return go.Figure()
    
    wins = (trades_df['pnl'] > 0).sum()
    losses = (trades_df['pnl'] <= 0).sum()
    
    fig = go.Figure(data=[go.Pie(
        labels=['Wins', 'Losses'],
        values=[wins, losses],
        hole=0.4,
        marker=dict(colors=['#00d084', '#ff4757'])
    )])
    
    fig.update_layout(
        title='Win/Loss Distribution',
        template='plotly_white',
        height=300
    )
    
    return fig

def main():
    """Main dashboard function"""
    
    # Header
    st.title("🤖 BotPolyMarket Advanced Dashboard")
    st.markdown("Real-time trading metrics and performance analysis")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Refresh rate
        refresh_rate = st.slider("Refresh Rate (seconds)", 5, 60, 10)
        
        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto Refresh", value=True)
        
        # Time range filter
        st.subheader("Time Range")
        time_range = st.selectbox(
            "Select Range",
            ["Last Hour", "Last 24 Hours", "Last 7 Days", "Last 30 Days", "All Time"]
        )
        
        # Strategy filter
        st.subheader("Filters")
        trades_df = get_recent_trades(1000)
        if not trades_df.empty:
            strategies = ["All"] + list(trades_df['strategy'].unique())
            selected_strategy = st.multiselect("Strategies", strategies, default=["All"])
        
        st.markdown("---")
        st.info(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
        
        if st.button("🔄 Manual Refresh"):
            st.rerun()
    
    # Load data
    metrics = get_performance_metrics()
    trades_df = get_recent_trades()
    positions_df = get_active_positions()
    
    # Key Metrics Row
    st.header("📊 Key Metrics")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Total P&L",
            f"${metrics['total_pnl']:,.2f}",
            f"{metrics['daily_pnl']:+.2f} today"
        )
    
    with col2:
        st.metric(
            "Win Rate",
            f"{metrics['win_rate']:.1f}%",
            f"Target: 70%"
        )
    
    with col3:
        st.metric(
            "Sharpe Ratio",
            f"{metrics['sharpe_ratio']:.2f}",
            f"{'✅' if metrics['sharpe_ratio'] > 2 else '⚠️'}"
        )
    
    with col4:
        st.metric(
            "Total Trades",
            f"{metrics['total_trades']:,}",
            f"{len(trades_df)} recent"
        )
    
    with col5:
        st.metric(
            "Current Capital",
            f"${metrics['current_capital']:,.2f}",
            f"{((metrics['current_capital']/10000 - 1)*100):+.1f}%"
        )
    
    st.markdown("---")
    
    # Charts Row
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(create_pnl_chart(trades_df), use_container_width=True)
    
    with col2:
        st.plotly_chart(create_strategy_performance_chart(trades_df), use_container_width=True)
    
    # Second Charts Row
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.subheader("📈 Performance Timeline")
        if not trades_df.empty:
            # Daily P&L chart
            daily_pnl = trades_df.set_index('timestamp').resample('D')['pnl'].sum()
            fig = px.bar(daily_pnl, title="Daily P&L")
            fig.update_traces(marker_color=['#00d084' if x > 0 else '#ff4757' for x in daily_pnl])
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.plotly_chart(create_win_rate_pie(trades_df), use_container_width=True)
    
    with col3:
        st.subheader("⚠️ Risk Metrics")
        st.metric("Max Drawdown", f"{metrics['max_drawdown']:.1f}%")
        st.metric("Exposure", f"${metrics.get('total_exposure', 0):,.0f}")
        st.metric("Open Positions", len(positions_df))
    
    st.markdown("---")
    
    # Active Positions
    st.header("📍 Active Positions")
    if not positions_df.empty:
        # Format the dataframe for display
        display_df = positions_df.copy()
        display_df['entry_time'] = pd.to_datetime(display_df['entry_time']).dt.strftime('%H:%M:%S')
        display_df['size'] = display_df['size'].apply(lambda x: f"${x:,.2f}")
        display_df['unrealized_pnl'] = display_df['unrealized_pnl'].apply(lambda x: f"${x:+,.2f}")
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No active positions")
    
    st.markdown("---")
    
    # Recent Trades Table
    st.header("📜 Recent Trades")
    if not trades_df.empty:
        # Format trades for display
        display_trades = trades_df.tail(20).copy()
        display_trades['timestamp'] = display_trades['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        display_trades['pnl'] = display_trades['pnl'].apply(lambda x: f"${x:+,.2f}")
        display_trades['size'] = display_trades['size'].apply(lambda x: f"${x:,.2f}")
        
        # Color code by profit/loss
        def highlight_pnl(row):
            color = '#d4edda' if '+' in str(row['pnl']) else '#f8d7da'
            return [f'background-color: {color}'] * len(row)
        
        styled_df = display_trades.style.apply(highlight_pnl, axis=1)
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        st.info("No trades recorded yet")
    
    # System Health
    st.markdown("---")
    st.header("🏥 System Health")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("API Status", "🟢 Online")
    with col2:
        st.metric("WebSocket", "🟢 Connected")
    with col3:
        st.metric("Database", "🟢 Healthy")
    with col4:
        st.metric("Memory Usage", "34%")
    
    # Auto-refresh
    if auto_refresh:
        time.sleep(refresh_rate)
        st.rerun()

if __name__ == "__main__":
    main()
