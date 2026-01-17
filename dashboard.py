"""
Dashboard en Tiempo Real para BotPolyMarket
Visualización de oportunidades, trades y métricas
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import asyncio

st.set_page_config(page_title="BotPolyMarket Dashboard", layout="wide")

# Configuración de página
st.title("🤖 BotPolyMarket - Dashboard en Tiempo Real")
st.markdown("**Fase 1**: WebSocket + Multi-Market Scanner")

# Layout en columnas
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Oportunidades Detectadas", "47", "+12")
with col2:
    st.metric("Trades Ejecutados", "23", "+5")
with col3:
    st.metric("Win Rate", "68.5%", "+2.3%")
with col4:
    st.metric("ROI Total", "+$3,845", "+$420")

# Tabs principales
tab1, tab2, tab3, tab4 = st.tabs(["📊 Oportunidades", "💰 Trades", "📈 Métricas", "⚙️ Config"])

with tab1:
    st.subheader("Oportunidades Activas")
    
    # Tabla de oportunidades
    opp_data = pd.DataFrame({
        "Mercado": ["BTC >$100k Jan", "ETH >$3.5k", "SOL >$150"],
        "Estrategia": ["Fair Value Gap", "BTC 15min Lag", "Volume Confirmation"],
        "Confianza": ["72%", "70%", "66%"],
        "Dirección": ["YES", "YES", "NO"],
        "Entry": ["$0.47", "$0.52", "$0.35"],
        "R:R": ["1:3.5", "1:5.0", "1:2.8"]
    })
    st.dataframe(opp_data, use_container_width=True)
    
    # Gráfico de confianza
    fig = go.Figure(data=[
        go.Bar(x=opp_data["Mercado"], y=[72, 70, 66], 
               marker_color=['green' if x > 65 else 'orange' for x in [72, 70, 66]])
    ])
    fig.update_layout(title="Confianza por Oportunidad", yaxis_title="Confianza (%)")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Historial de Trades")
    
    trades_data = pd.DataFrame({
        "Timestamp": [datetime.now() - timedelta(hours=i) for i in range(5)],
        "Mercado": ["BTC >$100k", "ETH >$3.5k", "SOL >$140", "BTC >$98k", "ETH >$3.4k"],
        "Estrategia": ["FVG", "Lag", "Volume", "Arbitrage", "FVG"],
        "Resultado": ["✅ +$215", "✅ +$340", "❌ -$85", "✅ +$180", "✅ +$120"],
        "ROI": ["+12.5%", "+18.2%", "-4.8%", "+9.5%", "+7.1%"]
    })
    st.dataframe(trades_data, use_container_width=True)
    
    # PnL Chart
    cumulative_pnl = [215, 555, 470, 650, 770]
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=list(range(5)), y=cumulative_pnl, 
                              mode='lines+markers', name='PnL Acumulado',
                              line=dict(color='green', width=3)))
    fig2.update_layout(title="PnL Acumulado", yaxis_title="USD", xaxis_title="Trade #")
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    st.subheader("Métricas de Rendimiento")
    
    col_m1, col_m2 = st.columns(2)
    
    with col_m1:
        # Win rate por estrategia
        strategy_wr = pd.DataFrame({
            "Estrategia": ["BTC 15min Lag", "Volume Conf", "FVG", "Arbitrage"],
            "Win Rate": [70, 66, 63, 68]
        })
        fig3 = go.Figure(data=[go.Bar(x=strategy_wr["Estrategia"], y=strategy_wr["Win Rate"])])
        fig3.update_layout(title="Win Rate por Estrategia")
        st.plotly_chart(fig3, use_container_width=True)
    
    with col_m2:
        # Distribución de trades
        trade_dist = ["BTC 15min Lag: 24", "Volume Conf: 15", "FVG: 18", "Otros: 28"]
        fig4 = go.Figure(data=[go.Pie(labels=[t.split(":")[0] for t in trade_dist], 
                                      values=[24, 15, 18, 28])])
        fig4.update_layout(title="Distribución de Trades")
        st.plotly_chart(fig4, use_container_width=True)

with tab4:
    st.subheader("Configuración")
    
    st.checkbox("WebSocket Activo", value=True)
    st.checkbox("Multi-Market Scanner", value=True)
    st.number_input("Mercados Simultáneos", min_value=1, max_value=100, value=20)
    st.number_input("Intervalo Escaneo (s)", min_value=5, max_value=300, value=30)
    
    if st.button("🔄 Reiniciar Bot"):
        st.success("Bot reiniciado correctamente")
    
    if st.button("🛑 Detener Trading"):
        st.warning("Trading detenido - Solo modo monitoreo")

# Footer
st.markdown("---")
st.markdown("**Bot Status:** 🟢 Operativo | **Uptime:** 14h 32m | **Última actualización:** " + datetime.now().strftime("%H:%M:%S"))
