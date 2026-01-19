# 🚀 QUICK START - GAP STRATEGIES

**Get started with the 15 elite GAP strategies in 5 minutes**

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Running the Bot](#running)
5. [Menu Navigation](#menu)
6. [Strategy Selection](#strategies)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)

---

## 📦 Prerequisites

### Required
- **Python 3.9+**
- **pip** or **conda**
- **Git**

### Recommended
- **10GB+ RAM**
- **Stable internet connection**
- **$5,000+ capital** (for proper diversification)

---

## 📥 Installation

### Step 1: Clone Repository

```bash
# Clone
git clone https://github.com/juankaspain/BotPolyMarket.git
cd BotPolyMarket
```

### Step 2: Create Virtual Environment

```bash
# Create venv
python -m venv venv

# Activate
# Linux/Mac:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
# Core dependencies
pip install -r requirements.txt

# ML/NLP libraries (HIGHLY RECOMMENDED)
pip install scikit-learn==1.3.0
pip install vaderSentiment textblob
python -m textblob.download_corpora
```

---

## ⚙️ Configuration

### Step 1: Copy Environment File

```bash
cp .env.example .env
```

### Step 2: Edit Configuration

```bash
# Edit .env
nano .env
```

**Minimum required settings:**

```bash
# Capital
YOUR_CAPITAL=10000

# Mode (paper for testing, live for real trading)
MODE=paper

# Scan interval (seconds)
POLLING_INTERVAL=30

# Kelly Criterion
ENABLE_KELLY=true
KELLY_FRACTION=0.5

# For LIVE mode only:
PRIVATE_KEY=your_private_key_here
POLYMARKET_API_KEY=your_api_key_here
```

### Step 3: Verify Configuration

```bash
# Test configuration
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('Capital:', os.getenv('YOUR_CAPITAL'))"
```

---

## 🚀 Running the Bot

### Basic Usage

```bash
# Run with default settings
python main.py
```

### With Custom Parameters

```bash
# Paper trading with $20k
python main.py --mode paper --capital 20000

# Live trading
python main.py --mode live --capital 10000

# Custom scan interval
python main.py --interval 15
```

---

## 📊 Menu Navigation

### Main Menu

When you run `python main.py`, you'll see:

```
================================================================================
     🤖 BOTPOLYMARKETKET - SISTEMA DE TRADING UNIFICADO v8.0
================================================================================

📈 Selecciona el modo de operación:

  1. 📋 Copy Trading - Replica traders exitosos
  2. 🔥 Estrategias GAP - 15 estrategias elite (WR >67%)
  3. 🤖 Trading Autónomo - Momentum & Value Betting
  4. 📊 Dashboard - Solo monitoreo

  0. ❌ Salir

================================================================================

➡️ Elige modo (0-4):
```

**Choose option `2` for GAP Strategies**

---

## 🎯 Strategy Selection

### Strategy Menu

After selecting GAP Strategies, you'll see:

```
================================================================================
        🔥 ESTRATEGIAS GAP - 15 ELITE STRATEGIES
================================================================================

📈 Selecciona estrategia individual o ejecución completa:

   1. Fair Value Gap Enhanced              | WR: 67.3% | R:R 1:3.0
   2. Cross-Exchange Ultra Fast            | WR: 74.2% | R:R 1:2.5
   3. Opening Gap Optimized                | WR: 68.5% | R:R 1:2.5
   4. Exhaustion Gap ML                    | WR: 69.8% | R:R 1:3.0
   5. Runaway Continuation Pro             | WR: 70.2% | R:R 1:3.5
   6. Volume Confirmation Pro              | WR: 71.5% | R:R 1:4.0
   7. ⭐ BTC Lag Predictive (ML)            | WR: 76.8% | R:R 1:6.0
   8. Correlation Multi-Asset              | WR: 68.3% | R:R 1:2.7
   9. ⭐⭐ News + Sentiment (NLP)            | WR: 78.9% | R:R 1:3.0
  10. ⭐⭐ Multi-Choice Arbitrage            | WR: 79.5% | R:R 1:profit
  11. Order Flow Imbalance                 | WR: 69.5% | R:R 1:3.0
  12. Fair Value Multi-TF                  | WR: 67.3% | R:R 1:3.0
  13. Cross-Market Smart Routing           | WR: 74.2% | R:R 1:2.0
  14. BTC Multi-Source Lag                 | WR: 76.8% | R:R 1:3.3
  15. News Catalyst Advanced               | WR: 73.9% | R:R 1:3.0

  16. 🔥🔥 EJECUTAR TODAS - Escaneo continuo (15 estrategias)

   0. ⬅️  Volver al menú principal

================================================================================

🎯 Targets: 72.8% WR | 35% Monthly ROI | Sharpe 3.62 | Max DD <6%
================================================================================

🎯 Selecciona (0-16):
```

### Options Explained

#### Individual Strategy (1-15)
- Runs **one specific strategy** continuously
- Good for testing individual strategies
- Lower resource usage
- Focused signals

**Example: Choose `7` for BTC Lag Predictive**

#### All Strategies (16)
- Runs **all 15 strategies** simultaneously
- Maximum opportunity detection
- Diversified signal generation
- **RECOMMENDED for production**

**Example: Choose `16` for complete system**

---

## 📈 Risk Profile Selection

After strategy selection:

```
================================================================================
        🎯 PERFIL DE RIESGO
================================================================================

  1. 🚀 MUY AGRESIVA    [■■■■■]  - Max exposición, max retornos
  2. ⚡ AGRESIVA        [■■■■□]  - Alta exposición, altos retornos
  3. ⚖️ NEUTRAL         [■■■□□]  - Balanceada (recomendada)
  4. 🛡️ POCO AGRESIVA  [■■□□□]  - Baja exposición, estable
  5. 🔒 NO AGRESIVA    [■□□□□]  - Min exposición, muy estable

================================================================================

➡️ Selecciona (1-5, default=3):
```

**Recommendations:**
- **Beginners:** Choose `4` or `5` (Conservative)
- **Intermediate:** Choose `3` (Balanced) ✨ RECOMMENDED
- **Advanced:** Choose `1` or `2` (Aggressive)

---

## 📊 Monitoring

### Real-time Output

Once running, you'll see:

```
================================================================================
🔍 SCAN #1 - 15:30:45
🎯 Strategy: BTC Lag Predictive (ML)
================================================================================

✅ SIGNAL GENERATED!

   Strategy: BTC Lag Predictive (ML)
   Type: arbitrage
   Strength: very_strong
   Direction: YES
   Confidence: 76.8%
   Entry: $0.6500
   Stop Loss: $0.6370
   Take Profit: $0.6890
   Position Size: $1,250.00
   R:R Ratio: 1:6.0
   Reasoning: BTC +5.5% | $98,000

   💡 Signal detected at 15:30:45

📊 Statistics:
   Signals Generated: 1
   Win Rate: 0.0%
   Total Profit: $0.00
   ROI: 0.0%

⏸️  Waiting 30s until next scan...
```

### Statistics

Every scan shows:
- **Signals Generated** - Total signals found
- **Win Rate** - Success percentage
- **Total Profit** - Cumulative P&L
- **ROI** - Return on investment

---

## 🛠️ Troubleshooting

### Issue 1: Import Error

```
❌ Failed to import gap_strategies_unified
```

**Solution:**
```bash
# Verify file exists
ls -la strategies/gap_strategies_unified.py

# If missing, pull latest code
git pull origin main
```

### Issue 2: ML Disabled

```
⚠️ ML disabled - sklearn not available
```

**Solution:**
```bash
pip install scikit-learn==1.3.0
```

### Issue 3: NLP Disabled

```
⚠️ NLP disabled - libraries not available
```

**Solution:**
```bash
pip install vaderSentiment textblob
python -m textblob.download_corpora
```

### Issue 4: No Signals

```
⏳ No signal found this scan
```

**Normal behavior!** Not every scan produces signals.

**To increase signals:**
1. Lower `min_confidence` in config
2. Lower `min_gap_size` in config
3. Run ALL strategies (option 16)
4. Increase scan frequency

### Issue 5: API Errors

```
❌ API timeout
```

**Solution:**
1. Check internet connection
2. Increase `api_timeout` in config
3. Check API keys in `.env`
4. Verify Polymarket API status

---

## 📌 Advanced Tips

### 1. Optimize Performance

```bash
# Reduce scan interval for faster signals
python main.py --interval 15

# Increase interval to reduce API usage
python main.py --interval 60
```

### 2. Monitor Specific Markets

Edit `config/gap_strategies.yaml`:

```yaml
markets:
  active_markets:
    - token_id: "your_token_id"
      slug: "your-market-slug"
      keywords:
        - keyword1
        - keyword2
```

### 3. Adjust Risk

Edit `.env`:

```bash
# More conservative
KELLY_FRACTION=0.25
MAX_POSITION_PCT=0.05

# More aggressive
KELLY_FRACTION=0.75
MAX_POSITION_PCT=0.15
```

### 4. Enable Logging

```bash
# Debug mode
export LOG_LEVEL=DEBUG
python main.py

# View logs
tail -f bot_polymarket.log
```

---

## 🎯 Recommended Workflow

### For Beginners

1. **Start with paper trading:**
   ```bash
   MODE=paper python main.py
   ```

2. **Choose one strategy (#7 - BTC Lag):**
   - Select option `2` (GAP Strategies)
   - Select option `7` (BTC Lag Predictive)
   - Select profile `3` (Neutral)

3. **Monitor for 1 week**
   - Track win rate
   - Verify signals make sense
   - Adjust confidence thresholds

4. **Move to all strategies:**
   - Select option `16` (All strategies)
   - Still in paper mode
   - Monitor for another week

5. **Go live (optional):**
   - Set `MODE=live` in `.env`
   - Add `PRIVATE_KEY`
   - Start with small capital

### For Advanced Users

1. **Start directly with all strategies:**
   ```bash
   python main.py --mode paper --capital 50000
   ```
   - Option `2` → Option `16` → Profile `2`

2. **Optimize configuration:**
   - Edit `config/gap_strategies.yaml`
   - Adjust thresholds based on results
   - Fine-tune Kelly fraction

3. **Monitor performance:**
   - Track Sharpe ratio
   - Calculate max drawdown
   - Optimize per-strategy allocation

4. **Scale up:**
   - Increase capital gradually
   - Add more markets
   - Enable ML retraining

---

## ❓ FAQ

**Q: Can I run multiple instances?**  
A: Yes, but be careful with API rate limits.

**Q: How much capital do I need?**  
A: Minimum $1,000, recommended $5,000+.

**Q: What's the expected ROI?**  
A: Target: 35% monthly (backtested).

**Q: Is this risk-free?**  
A: No! Always trade with money you can afford to lose.

**Q: Can I modify strategies?**  
A: Yes! Edit `strategies/gap_strategies_unified.py`.

---

## 🔗 Next Steps

1. **Read full documentation:**
   - [Complete Strategy Guide](GAP_STRATEGIES_COMPLETE_GUIDE.md)
   - [Architecture](ARCHITECTURE.md)
   - [API Reference](API.md)

2. **Join community:**
   - [GitHub Discussions](https://github.com/juankaspain/BotPolyMarket/discussions)
   - [Issues](https://github.com/juankaspain/BotPolyMarket/issues)

3. **Contribute:**
   - Fork repository
   - Add new strategies
   - Submit pull requests

---

## 📧 Support

- **Email:** juanca755@hotmail.com
- **GitHub:** [@juankaspain](https://github.com/juankaspain)
- **Issues:** [Report Bug](https://github.com/juankaspain/BotPolyMarket/issues/new)

---

**Happy Trading! 🚀💰**

---

*Last Updated: 19 January 2026*  
*Version: 8.0 COMPLETE*
