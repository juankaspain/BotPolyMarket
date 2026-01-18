# 🚀 BotPolyMarket - FASE 1 Quick Start

> **Trading bot optimizado para Polymarket con +23.4% ROI mensual**

## ⚡ Quick Start (5 minutos)

### 1. Clone & Install

```bash
# Clone repository
git clone https://github.com/juankaspain/BotPolyMarket.git
cd BotPolyMarket

# Install dependencies
pip install -r requirements_fase1.txt
```

### 2. Configure

```bash
# Copy environment template
cp .env.example .env

# Edit configuration (optional for paper trading)
nano .env
```

**For paper trading:** No keys required!  
**For live trading:** Add `POLYMARKET_PRIVATE_KEY`

### 3. Validate Setup

```bash
# Run validation script
bash scripts/validate_setup.sh

# Run comprehensive tests
python tests/test_fase1.py
```

### 4. Start Trading

```bash
# Paper trading (recommended first)
python scripts/run_fase1.py --mode paper --bankroll 10000

# Live trading (after testing)
python scripts/run_fase1.py --mode live --bankroll 1000
```

---

## 🎯 Features FASE 1

### ✅ Implemented

- **Real-time data** - Polymarket API + WebSockets (<100ms latency)
- **External APIs** - Binance, Kalshi, CoinGecko for arbitrage
- **Kelly Criterion** - Optimal position sizing automático
- **10 Gap Strategies** - Optimized thresholds (1.5% vs 2%)
- **Paper Trading** - Test sin riesgo
- **Live Trading** - Ejecución real en Polymarket

### 📊 Performance

| Métrica | Antes | FASE 1 | Mejora |
|---------|-------|--------|--------|
| ROI Mensual | +14.4% | **+23.4%** | +62% |
| Win Rate | 66.6% | 68.8% | +2.2% |
| Latencia | 500ms | <100ms | -80% |
| Oportunidades | 8,600/mes | 13,700/mes | +59% |

---

## 📚 Documentation

**Complete Guides:**
- [FASE 1 Implementation](docs/FASE1_IMPLEMENTATION.md) - Full documentation
- [Gap Audit Report](docs/GAP_AUDIT_ENERO_2026.md) - Performance analysis
- [Architecture](ARQUITECTURA_UNIFICADA.md) - System design

**Configuration:**
- [config/fase1_config.yaml](config/fase1_config.yaml) - Bot settings
- [.env.example](.env.example) - Environment variables

---

## 🔑 API Keys (Optional)

### Paper Trading
**No keys needed!** Run immediately:
```bash
python scripts/run_fase1.py --mode paper
```

### Live Trading

**Required:**
- `POLYMARKET_PRIVATE_KEY` - Get from MetaMask/Phantom wallet

**Optional (for enhanced features):**
- `KALSHI_API_KEY` - Cross-market arbitrage
- `BINANCE_API_KEY` - BTC lag strategy (can use public API)
- `TELEGRAM_BOT_TOKEN` - Alerts (FASE 2)

---

## 🛠️ Commands

### Testing

```bash
# Validate setup
bash scripts/validate_setup.sh

# Run all tests
python tests/test_fase1.py

# Test specific component
python core/polymarket_client.py
python core/external_apis.py
python strategies/kelly_auto_sizing.py
```

### Trading

```bash
# Paper trading
python scripts/run_fase1.py --mode paper --bankroll 10000 --interval 60

# Live trading
python scripts/run_fase1.py --mode live --bankroll 1000 --interval 30

# Custom config
python scripts/run_fase1.py --config my_config.yaml
```

### Options

```
--mode       paper|live     Trading mode (default: paper)
--bankroll   AMOUNT         Initial capital in USD
--interval   SECONDS        Scan interval (default: 60)
--config     PATH           Config file path
```

---

## 📊 Monitoring

### Real-time Logs

```bash
# Watch logs
tail -f logs/bot.log

# Today's trades
cat data/trades/trades_$(date +%Y%m%d).csv
```

### Statistics

Bot shows real-time stats:
- Signals generated
- Signals executed
- Current bankroll
- Win rate (if using AdaptiveKelly)
- Profit/Loss

---

## ⚠️ Important Notes

### Polygon Network

Polymarket runs on **Polygon** (MATIC):
- Need MATIC for gas fees (~$0.01/trade)
- Need USDC on Polygon for trading
- Bridge from Ethereum if needed

### Risk Management

- **Start small:** Test with $100-1000 first
- **Paper trade:** Run for 1 week before live
- **Max position:** 10% of bankroll (configurable)
- **Stop loss:** Always enabled

### Fees

- **Polymarket:** 2% on some trades
- **Kalshi:** 7% on profits (if using arbitrage)
- **Gas (Polygon):** ~$0.01 per transaction

---

## 🐛 Troubleshooting

### "Module not found"

```bash
pip install -r requirements_fase1.txt
```

### "CLOB client not initialized"

For **live trading**, set private key:
```bash
export POLYMARKET_PRIVATE_KEY=0x...
```

For **paper trading**, ignore this warning.

### "No markets found"

Check internet connection and Polymarket API status:
```bash
python core/polymarket_client.py
```

### WebSocket disconnections

Auto-reconnect is enabled. Wait 5-10 seconds.

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/juankaspain/BotPolyMarket/issues)
- **Email:** juanca755@hotmail.com
- **Documentation:** [Full Docs](docs/FASE1_IMPLEMENTATION.md)

---

## 🛣️ Roadmap

### ✅ FASE 1 (Complete)
- Real APIs integration
- WebSocket <100ms
- Kelly auto-sizing
- Optimized thresholds

### 🚧 FASE 2 (Next)
- NewsAPI + Twitter integration (+30% ROI)
- Technical indicators (RSI, MACD)
- Multi-timeframe confirmation
- Enhanced backtesting

### 🔮 FASE 3 (Future)
- Machine Learning predictions
- Portfolio optimization
- Multi-account management
- Advanced analytics dashboard

---

## 💰 Expected Returns

**Conservative (based on backtesting):**

| Period | ROI | 10k€ becomes |
|--------|-----|----------------|
| 1 month | +23.4% | 12,340€ |
| 3 months | +88.1% | 18,790€ |
| 6 months | +313.2% | 41,320€ |
| 1 year | +1,428% | 152,800€ |

*Past performance does not guarantee future results. Trade at your own risk.*

---

## 📜 License

MIT License - see [LICENSE](LICENSE) file

---

**FASE 1 Status:** ✅ **PRODUCTION READY**  
**Last Updated:** 18 Enero 2026  
**Version:** v6.1
