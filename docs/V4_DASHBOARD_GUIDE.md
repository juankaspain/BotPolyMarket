# v4.0 Enterprise Dashboard - User Guide

## 🎯 Overview

Dashboard profesional para monitoreo en tiempo real del BotPolyMarket con métricas avanzadas de riesgo y performance.

## 🚀 Quick Start

### Instalación

```bash
# Instalar dependencias
pip install -r requirements.txt

# Lanzar dashboard
bash dashboard/launch.sh
```

### Acceso

- **URL:** http://localhost:8501
- **Puerto:** 8501
- **Tema:** Dark mode por defecto

## 📊 Features

### 1. Portfolio Overview

**Métricas principales:**
- Total Capital
- Available Cash
- Total PnL
- Active Positions

**Visualización:**
- Cards con métricas en tiempo real
- Indicadores de cambio (daily %)
- Color-coded (verde/rojo)

### 2. Performance Analytics

**PnL Chart:**
- Gráfico de 30 días
- Cumulative PnL
- Interactive Plotly charts

**Risk Metrics:**
- **Sharpe Ratio:** Retorno ajustado por riesgo
- **Max Drawdown:** Pérdida máxima desde peak
- **Win Rate:** % de trades ganadores

### 3. Active Positions

**Tabla con:**
- Market ID
- Entry/Current Price
- Position Size
- PnL real-time
- Strategy utilizada

### 4. Trade History

**Features:**
- Últimos 50 trades
- Filtros por estrategia
- Filtros por outcome (WIN/LOSS)
- Date range selector
- **Export CSV:** Descarga historial completo

## ⚙️ Settings Panel

### Trading Mode
- Paper Trading (simulación)
- Live Trading (real money)

### Active Strategies
- ✅ Gap Predictor
- ✅ Arbitrage
- ✅ ML Enhanced

### Risk Parameters
- Max Position Size: 1-20%
- Max Total Exposure: 10-100%

### Controls
- ▶️ Start Bot
- ⏸️ Pause Bot
- 🔄 Reset Stats

## 📈 Risk Metrics Explained

### Sharpe Ratio
```
Sharpe = (Return - Risk-Free Rate) / Volatility
```

**Interpretación:**
- > 2.0: Excellent
- 1.0 - 2.0: Good
- < 1.0: Moderate

### Max Drawdown
```
DD = (Peak Value - Trough Value) / Peak Value
```

**Saludable:**
- < 10%: Muy bajo riesgo
- 10-20%: Riesgo moderado
- > 20%: Alto riesgo

### Win Rate
```
Win Rate = Winning Trades / Total Trades
```

**Metas v4.0:**
- Target: > 65%
- ML Enhanced: 78% (v2.0 goal)

## 🔧 Customization

### Cambiar tema

Editar `dashboard/launch.sh`:

```bash
streamlit run dashboard/streamlit_app.py \
    --theme.primaryColor "#ff0000"  # Cambiar color
```

### Añadir nuevas métricas

Editar `dashboard/streamlit_app.py`:

```python
def render_custom_metric(self):
    st.metric("My Metric", value, delta)
```

## 📱 Multi-Wallet Support (v4.0)

### Wallets soportadas:
- 🔮 Phantom (Solana)
- 🦊 MetaMask (Ethereum)
- 🐰 Rabby Wallet

### Conexión:

```python
from core.wallet_manager import WalletManager

wallet = WalletManager()
wallet.connect('phantom')
```

## 📥 Export & Audit Logs

### CSV Export

**Incluye:**
- Timestamp
- Market
- Strategy
- Entry/Exit prices
- PnL
- Outcome

**Uso:**
1. Ir a "History" tab
2. Aplicar filtros deseados
3. Click "📥 Export CSV"

### Audit Logs

Todos los trades se guardan automáticamente en:
```
logs/trades_YYYYMMDD.csv
logs/audit_YYYYMMDD.log
```

## 🐳 Docker Deployment

### Build

```bash
docker build -t botpolymarket-dashboard .
```

### Run

```bash
docker run -p 8501:8501 botpolymarket-dashboard
```

### Docker Compose

```yaml
services:
  dashboard:
    build: .
    ports:
      - "8501:8501"
    environment:
      - TRADING_MODE=paper
    volumes:
      - ./data:/app/data
```

## 🎯 ROI Meta v4.0

**Objetivos:**
- ROI: +150%
- Soporte: 10k€ capital
- Lanzamiento: Marzo 2026

**Métricas de éxito:**
- Dashboard uptime: 99.9%
- Response time: < 500ms
- Data refresh: < 30s

## 🔗 Integration con VPS

### Setup en VPS

```bash
# Instalar en servidor
ssh user@vps
git clone https://github.com/juankaspain/BotPolyMarket.git
cd BotPolyMarket

# Instalar dependencias
pip install -r requirements.txt

# Configurar como servicio
sudo systemctl enable botpolymarket-dashboard
sudo systemctl start botpolymarket-dashboard
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name dashboard.botpolymarket.com;
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 📞 Support

**Issues:** https://github.com/juankaspain/BotPolyMarket/issues
**Docs:** https://github.com/juankaspain/BotPolyMarket/docs

---

**v4.0 Enterprise Dashboard** | Marzo 2026 | BotPolyMarket
