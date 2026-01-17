#!/usr/bin/env python3
"""
v4.0 Enterprise Dashboard - Streamlit Interface
Dashboard profesional con métricas en tiempo real
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import Database
from core.portfolio_manager import PortfolioManager
from core.risk_manager import RiskManager

# Configuración de página
st.set_page_config(
    page_title="BotPolyMarket Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados
st.markdown("""
<style>
    .big-metric {
        font-size: 2.5rem;
        font-weight: bold;
    }
    .positive {
        color: #00ff00;
    }
    .negative {
        color: #ff0000;
    }
    .stMetric {
        background-color: #1e1e1e;
        padding: 15px;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

class DashboardApp:
    """Aplicación principal del dashboard"""
    
    def __init__(self):
        self.db = Database()
        self.portfolio = PortfolioManager()
        self.risk_manager = RiskManager()
        
    def render_header(self):
        """Renderiza header del dashboard"""
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.title("🤖 BotPolyMarket Enterprise Dashboard")
            st.caption("v4.0 - Real-time Trading Analytics")
        
        with col2:
            st.metric(
                "Status",
                "🟢 LIVE" if self._is_bot_running() else "🔴 OFFLINE"
            )
        
        with col3:
            st.metric(
                "Last Update",
                datetime.now().strftime("%H:%M:%S")
            )
    
    def render_portfolio_overview(self):
        """Panel de overview del portfolio"""
        st.header("💼 Portfolio Overview")
        
        # Obtener datos del portfolio
        portfolio_data = self.portfolio.get_current_state()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Capital",
                f"€{portfolio_data['total_value']:,.2f}",
                f"{portfolio_data['daily_change']:+.2f}%"
            )
        
        with col2:
            st.metric(
                "Available Cash",
                f"€{portfolio_data['cash']:,.2f}",
                f"{portfolio_data['cash_pct']:.1f}%"
            )
        
        with col3:
            st.metric(
                "Total PnL",
                f"€{portfolio_data['total_pnl']:,.2f}",
                f"{portfolio_data['roi']:.2f}%"
            )
        
        with col4:
            st.metric(
                "Active Positions",
                portfolio_data['active_positions'],
                f"€{portfolio_data['exposure']:,.2f}"
            )
    
    def render_pnl_chart(self):
        """Gráfico de PnL histórico"""
        st.header("📈 Profit & Loss")
        
        # Obtener datos históricos
        pnl_data = self._get_pnl_history(days=30)
        
        fig = go.Figure()
        
        # Línea de PnL acumulado
        fig.add_trace(go.Scatter(
            x=pnl_data['date'],
            y=pnl_data['cumulative_pnl'],
            mode='lines',
            name='Cumulative PnL',
            line=dict(color='#00ff00', width=3),
            fill='tozeroy'
        ))
        
        fig.update_layout(
            title="30-Day Cumulative PnL",
            xaxis_title="Date",
            yaxis_title="PnL (€)",
            template="plotly_dark",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_risk_metrics(self):
        """Panel de métricas de riesgo"""
        st.header("⚠️ Risk Metrics")
        
        risk_data = self.risk_manager.calculate_metrics()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("Sharpe Ratio")
            sharpe = risk_data['sharpe_ratio']
            st.metric("", f"{sharpe:.2f}", "Excellent" if sharpe > 2 else "Good" if sharpe > 1 else "Moderate")
            st.progress(min(sharpe / 3, 1.0))
        
        with col2:
            st.subheader("Max Drawdown")
            drawdown = risk_data['max_drawdown']
            st.metric("", f"{drawdown:.2%}", delta_color="inverse")
            st.progress(abs(drawdown))
        
        with col3:
            st.subheader("Win Rate")
            win_rate = risk_data['win_rate']
            st.metric("", f"{win_rate:.1%}")
            st.progress(win_rate)
    
    def render_active_positions(self):
        """Tabla de posiciones activas"""
        st.header("🎯 Active Positions")
        
        positions = self.portfolio.get_active_positions()
        
        if not positions:
            st.info("No active positions")
            return
        
        df = pd.DataFrame(positions)
        
        # Formatear columnas
        df['entry_price'] = df['entry_price'].apply(lambda x: f"€{x:.4f}")
        df['current_price'] = df['current_price'].apply(lambda x: f"€{x:.4f}")
        df['pnl'] = df['pnl'].apply(lambda x: f"€{x:+.2f}")
        df['size'] = df['size'].apply(lambda x: f"€{x:.2f}")
        
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )
    
    def render_trade_history(self):
        """Historial de trades recientes"""
        st.header("📜 Recent Trades")
        
        trades = self._get_recent_trades(limit=50)
        
        df = pd.DataFrame(trades)
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        
        with col1:
            strategy_filter = st.multiselect(
                "Strategy",
                options=df['strategy'].unique(),
                default=df['strategy'].unique()
            )
        
        with col2:
            outcome_filter = st.multiselect(
                "Outcome",
                options=['WIN', 'LOSS', 'OPEN'],
                default=['WIN', 'LOSS', 'OPEN']
            )
        
        with col3:
            date_range = st.date_input(
                "Date Range",
                value=(datetime.now() - timedelta(days=7), datetime.now())
            )
        
        # Aplicar filtros
        filtered_df = df[
            (df['strategy'].isin(strategy_filter)) &
            (df['outcome'].isin(outcome_filter))
        ]
        
        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Botón de exportación
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Export CSV",
            data=csv,
            file_name=f"trades_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    def render_settings(self):
        """Panel de configuración"""
        st.sidebar.header("⚙️ Settings")
        
        # Modo de trading
        trading_mode = st.sidebar.selectbox(
            "Trading Mode",
            ["Paper Trading", "Live Trading"]
        )
        
        # Estrategias activas
        st.sidebar.subheader("Active Strategies")
        gap_enabled = st.sidebar.checkbox("Gap Predictor", value=True)
        arb_enabled = st.sidebar.checkbox("Arbitrage", value=True)
        ml_enabled = st.sidebar.checkbox("ML Enhanced", value=True)
        
        # Parámetros de riesgo
        st.sidebar.subheader("Risk Parameters")
        max_position = st.sidebar.slider(
            "Max Position Size (%)",
            min_value=1,
            max_value=20,
            value=10
        )
        
        max_exposure = st.sidebar.slider(
            "Max Total Exposure (%)",
            min_value=10,
            max_value=100,
            value=80
        )
        
        # Botones de control
        st.sidebar.subheader("Controls")
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            if st.button("▶️ Start", use_container_width=True):
                st.success("Bot started!")
        
        with col2:
            if st.button("⏸️ Pause", use_container_width=True):
                st.warning("Bot paused!")
        
        if st.sidebar.button("🔄 Reset Stats", use_container_width=True):
            st.error("Stats reset!")
    
    def _is_bot_running(self) -> bool:
        """Verifica si el bot está corriendo"""
        # Implementación simplificada
        return True
    
    def _get_pnl_history(self, days: int) -> pd.DataFrame:
        """Obtiene historial de PnL"""
        # Datos de ejemplo - en producción vendría de DB
        dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
        pnl = pd.DataFrame({
            'date': dates,
            'daily_pnl': [50 + i*10 + (i % 5 - 2)*30 for i in range(days)]
        })
        pnl['cumulative_pnl'] = pnl['daily_pnl'].cumsum()
        return pnl
    
    def _get_recent_trades(self, limit: int) -> list:
        """Obtiene trades recientes"""
        # Datos de ejemplo
        return [
            {
                'timestamp': datetime.now() - timedelta(hours=i),
                'market': f'Market_{i}',
                'strategy': ['Gap', 'Arbitrage', 'ML'][i % 3],
                'side': 'YES' if i % 2 else 'NO',
                'size': 100 + i*10,
                'entry': 0.45 + (i % 10) * 0.01,
                'exit': 0.55 + (i % 10) * 0.01,
                'pnl': (10 - i % 20),
                'outcome': ['WIN', 'LOSS', 'OPEN'][i % 3]
            }
            for i in range(limit)
        ]
    
    def run(self):
        """Ejecuta la aplicación principal"""
        self.render_settings()
        self.render_header()
        
        # Tabs principales
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Overview",
            "📈 Performance",
            "🎯 Positions",
            "📜 History"
        ])
        
        with tab1:
            self.render_portfolio_overview()
            self.render_risk_metrics()
        
        with tab2:
            self.render_pnl_chart()
        
        with tab3:
            self.render_active_positions()
        
        with tab4:
            self.render_trade_history()
        
        # Auto-refresh
        st.sidebar.markdown("---")
        auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=True)
        
        if auto_refresh:
            import time
            time.sleep(30)
            st.rerun()

if __name__ == "__main__":
    app = DashboardApp()
    app.run()
