# 🚀 Getting Started - BotPolyMarket FASE 1

**Guía paso a paso** para poner en marcha el bot con las optimizaciones FASE 1.

---

## 📋 Prerequisites

### Sistema
- **Python:** 3.11 o superior
- **OS:** Linux, macOS, o Windows (WSL recomendado)
- **RAM:** Mínimo 4GB, recomendado 8GB
- **Disk:** 2GB libres

### Conocimientos
- Básico de Python
- Básico de terminal/command line
- Conocimiento de mercados de predicción (recomendado)

---

## 💻 Instalación
### Paso 1: Clonar el Repositorio

```bash
# Clonar
git clone https://github.com/juankaspain/BotPolyMarket.git
cd BotPolyMarket

# Verificar versión
cat VERSION  # Debe mostrar v6.1-FASE1 o superior
```

### Paso 2: Crear Virtual Environment

```bash
# Crear venv
python3.11 -m venv venv

# Activar
# Linux/Mac:
source venv/bin/activate

# Windows:
venv\Scripts\activate

# Verificar
which python  # Debe apuntar a venv/bin/python
```

### Paso 3: Instalar Dependencias

```bash
# Instalar FASE 1
pip install -r requirements_fase1.txt

# Verificar instalación
pip list | grep -E "py-clob-client|ccxt|websocket"
```

**Expected output:**
```
ccxt                4.2.0
py-clob-client      0.20.0
websocket-client    1.6.0
websockets          12.0
```

---

## ⚡ Configuración

### Paso 4: Environment Variables

```bash
# Copiar template
cp .env.example .env

# Editar
nano .env  # o vim, code, etc.
```

**Mínimo requerido (Paper Trading):**
```bash
TRADING_MODE=paper
BANKROLL=10000
```

**Para Live Trading:**
```bash
TRADING_MODE=live
BANKROLL=1000  # Empezar con poco capital

# Polymarket (REQUERIDO)
POLYMARKET_PRIVATE_KEY=0x...
POLYMARKET_CHAIN_ID=137

# Kalshi (OPCIONAL - mejora arbitraje)
KALSHI_API_KEY=your_key

# Telegram (OPCIONAL - alertas)
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Paso 5: Obtener API Keys

#### Polymarket (Para Live Trading)

1. **Crear cuenta:** https://polymarket.com/
2. **Conectar wallet:** MetaMask u otra wallet Web3
3. **Exportar private key:**
   - MetaMask → Account Details → Export Private Key
   - ⚠️ **NUNCA compartir esta clave**
4. **Añadir a .env:**
   ```bash
   POLYMARKET_PRIVATE_KEY=0xYOUR_PRIVATE_KEY
   ```

#### Kalshi (Opcional - Cross-Market Arbitrage)

1. **Crear cuenta:** https://kalshi.com/
2. **API Access:** Settings → API → Generate Key
3. **Añadir a .env:**
   ```bash
   KALSHI_API_KEY=YOUR_KALSHI_KEY
   ```

#### Telegram (Opcional - Alertas)

1. **Crear bot:**
   - Telegram → @BotFather → /newbot
   - Seguir instrucciones
   - Copiar token

2. **Obtener Chat ID:**
   - Telegram → @userinfobot → /start
   - Copiar tu User ID

3. **Añadir a .env:**
   ```bash
   TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
   TELEGRAM_CHAT_ID=123456789
   ```

---

## 🧪 Testing

### Paso 6: Ejecutar Tests

```bash
# Test suite completo
python scripts/test_fase1.py
```

**Si todo está bien:**
```
🧪 FASE 1 TESTING SUITE
================================================================================

📋 TEST 1: Polymarket Client
✅ Client initialization                                  [PASS]
✅ Get markets                                            [PASS]
   Retrieved 10 markets
✅ Get market data                                        [PASS]
   Price: $0.6547

...

📋 TEST SUMMARY
✅ Passed:  15/20
❌ Failed:  0/20
⏩ Skipped: 5/20

🎉 ALL TESTS PASSED!
```

**Si hay errores:**

1. **`ModuleNotFoundError: No module named 'ccxt'`**
   ```bash
   pip install -r requirements_fase1.txt
   ```

2. **`CLOB client not initialized`**
   ```bash
   # Añadir en .env:
   POLYMARKET_PRIVATE_KEY=0x...
   ```

3. **`Error fetching BTC price`**
   - Verificar conexión a internet
   - Binance API puede estar temporalmente caído (usa Coinbase como backup)

---

## 🟢 Ejecución

### Paso 7: Paper Trading (Recomendado Primero)

**Qué es Paper Trading:**
- Simula trades sin dinero real
- Detecta señales reales del mercado
- Guarda trades en CSV para análisis
- **Sin riesgo financiero**

**Ejecutar:**
```bash
python scripts/run_fase1.py --mode paper --bankroll 10000 --interval 60
```

**Opciones:**
- `--mode paper` - Paper trading (simulado)
- `--bankroll 10000` - Capital inicial (USD)
- `--interval 60` - Segundos entre escaneos

**Output esperado:**
```
================================================================================
🚀 BotPolyMarket - FASE 1 OPTIMIZED
================================================================================
Mode: PAPER
Bankroll: $10,000.00
Kelly: 0.5 (Half Kelly)
Min Gap: 1.5%
================================================================================

🟢 Bot started - Press Ctrl+C to stop

================================================================================
🔄 Iteration #1 - 03:45:12
================================================================================

🔍 Scanning 50 markets...
✅ Found 3 signal(s)

--------------------------------------------------------------------------------
📢 SIGNAL DETECTED
--------------------------------------------------------------------------------
Strategy:    BTC Lag Arbitrage (Optimized)
Direction:   YES
Confidence:  73%
Win Rate:    73%
R:R Ratio:   1:5
Entry:       $0.6547
Stop Loss:   $0.6482
Take Profit: $0.6874
Position:    $547.23 (5.47% risk)
Reasoning:   BTC moved +5.2% ($98,245)
--------------------------------------------------------------------------------

📋 PAPER TRADE - Not executed

📊 Other signals:
  #2: Cross-Market Arbitrage (Optimized) (71%)
  #3: Fair Value Gap (Optimized) (65%)

📊 Stats: 3 signals generated
Bankroll: $10,000.00

⏸️ Waiting 60s until next scan...
```

**Detener:**
- Presiona `Ctrl+C`
- El bot hará shutdown limpio y mostrará estadísticas finales

### Paso 8: Analizar Resultados (Paper Trading)

**Ver trades guardados:**
```bash
# Trades del día
cat data/trades/trades_$(date +%Y%m%d).csv

# Formato CSV
head -5 data/trades/trades_20260118.csv
```

**Output:**
```csv
timestamp,strategy,direction,confidence,entry,stop,target,size,risk_pct,executed,order_id
2026-01-18T03:45:12,BTC Lag Arbitrage (Optimized),YES,73,0.6547,0.6482,0.6874,547.23,5.47,False,
2026-01-18T04:01:34,Cross-Market Arbitrage (Optimized),YES,71,0.5234,0.5077,0.5548,423.18,4.23,False,
```

**Análisis recomendado:**
```python
import pandas as pd

# Cargar trades
df = pd.read_csv('data/trades/trades_20260118.csv')

# Estadísticas
print(f"Total signals: {len(df)}")
print(f"Avg confidence: {df['confidence'].mean():.1f}%")
print(f"Avg size: ${df['size'].mean():.2f}")
print(f"Avg risk: {df['risk_pct'].mean():.2f}%")

# Por estrategia
print("\nBy strategy:")
print(df.groupby('strategy')['confidence'].agg(['count', 'mean']))
```

### Paso 9: Live Trading (Después de Validar Paper)

⚠️ **IMPORTANTE:** Solo pasar a live después de:
1. Ejecutar paper trading por al menos **1 semana**
2. Verificar win rate >65%
3. Revisar que las señales tienen sentido
4. Empezar con **capital pequeño** (500-1000 USD)

**Preparación:**

1. **Fondos en wallet:**
   - USDC en Polygon network
   - MATIC para gas fees (0.1-0.5 MATIC suficiente)
   - Bridge desde Ethereum si es necesario: https://wallet.polygon.technology/

2. **Configurar .env:**
   ```bash
   TRADING_MODE=live
   BANKROLL=1000  # Empezar conservador
   POLYMARKET_PRIVATE_KEY=0x...
   ```

3. **Ejecutar:**
   ```bash
   # Confirmar configuración
   cat .env | grep TRADING_MODE
   
   # Ejecutar con capital limitado
   python scripts/run_fase1.py --mode live --bankroll 1000 --interval 30
   ```

**Diferencias vs Paper:**
- Ejecuta trades REALES en Polymarket
- Gasta MATIC en gas fees
- Trades aparecen en tu wallet Polymarket
- **RIESGO REAL de pérdida**

**Monitoreo:**
```bash
# En otra terminal, monitorear trades
tail -f data/trades/trades_$(date +%Y%m%d).csv

# Ver balance en tiempo real
watch -n 10 'python -c "from core.polymarket_client import PolymarketClient; import asyncio; client = PolymarketClient(); print(asyncio.run(client.get_balance()))"'
```

---

## 📊 Optimización

### Paso 10: Ajustar Parámetros

**Editar config:**
```bash
nano config/fase1_config.yaml
```

**Parámetros clave:**

```yaml
kelly:
  fraction: 0.5  # 0.25 = más conservador, 0.75 = más agresivo
  max_position_pct: 0.10  # Máximo 10% del bankroll por trade

gap_strategies:
  min_gap_size: 0.015  # 1.5% - reducir a 0.012 para más señales
  min_confidence: 60   # Mínimo 60% - aumentar a 65% para más calidad
  
  btc_lag:
    min_lag: 0.008  # 0.8% - muy sensible, considerar 0.01 (1%)
```

**Recomendaciones:**

| Perfil | Kelly | Max Position | Min Gap | Min Confidence |
|--------|-------|--------------|---------|----------------|
| **Conservador** | 0.25 | 0.05 | 0.020 | 70 |
| **Balanceado** | 0.50 | 0.10 | 0.015 | 60 |
| **Agresivo** | 0.75 | 0.15 | 0.012 | 55 |

### Paso 11: Monitoreo Continuo

**Dashboard (Opcional - FASE 4):**
```bash
# Si tienes Streamlit instalado
streamlit run dashboard/streamlit_app.py

# Abrir: http://localhost:8501
```

**Logs:**
```bash
# Ver logs en tiempo real
tail -f logs/bot.log

# Filtrar errores
grep ERROR logs/bot.log

# Filtrar trades ejecutados
grep "Order placed" logs/bot.log
```

**Alertas Telegram:**
- Si configuraste Telegram, recibirás alertas automáticas
- Cada señal detectada
- Cada trade ejecutado
- Errores críticos

---

## ⚠️ Troubleshooting

### Problema: No encuentra señales

**Síntoma:**
```
⚠️ No signals found
```

**Soluciones:**
1. **Reducir umbrales:**
   ```yaml
   min_gap_size: 0.012  # De 0.015 a 0.012
   min_confidence: 55   # De 60 a 55
   ```

2. **Aumentar mercados escaneados:**
   ```python
   # En run_fase1.py, línea ~80
   markets = await self.poly.get_markets(limit=100)  # De 50 a 100
   ```

3. **Verificar APIs externas:**
   ```bash
   python core/external_apis.py  # Test manual
   ```

### Problema: Error de conexión

**Síntoma:**
```
Error fetching markets: Connection timeout
```

**Soluciones:**
1. Verificar internet
2. Polymarket API puede estar caído (raro)
3. Usar VPN si estás en país restringido

### Problema: Error al ejecutar trade

**Síntoma:**
```
❌ Order failed
```

**Soluciones:**
1. **Verificar balance:**
   - Necesitas USDC suficiente
   - Necesitas MATIC para gas

2. **Verificar private key:**
   ```bash
   echo $POLYMARKET_PRIVATE_KEY
   # Debe empezar con 0x
   ```

3. **Network correcto:**
   ```bash
   # Debe ser Polygon (137)
   grep CHAIN_ID .env
   ```

### Problema: Kelly size muy pequeño

**Síntoma:**
```
Position too small ($5.23 < $10)
```

**Soluciones:**
1. **Aumentar bankroll:**
   ```bash
   --bankroll 20000  # De 10000 a 20000
   ```

2. **Reducir min_position_usd:**
   ```yaml
   kelly:
     min_position_usd: 5  # De 10 a 5
   ```

---

## 📚 Recursos Adicionales

### Documentación
- **[FASE 1 Implementation](FASE1_IMPLEMENTATION.md)** - Guía técnica completa
- **[Gap Audit](GAP_AUDIT_ENERO_2026.md)** - Análisis de estrategias
- **[API Reference](V6_INSTITUTIONAL_API.md)** - Documentación API

### Comunidad
- **GitHub Issues:** https://github.com/juankaspain/BotPolyMarket/issues
- **Discussions:** https://github.com/juankaspain/BotPolyMarket/discussions

### Educación
- **Polymarket Docs:** https://docs.polymarket.com/
- **Kelly Criterion:** https://en.wikipedia.org/wiki/Kelly_criterion
- **Prediction Markets:** https://en.wikipedia.org/wiki/Prediction_market

---

## ✅ Checklist de Validación

Antes de pasar a live, asegurarse de:

- [ ] Tests pasan (15+ passed)
- [ ] Paper trading ejecutado 7+ días
- [ ] Win rate >65% en paper
- [ ] Revisado manual de al menos 20 señales
- [ ] Configurado Telegram alerts
- [ ] USDC + MATIC en wallet Polygon
- [ ] Backup de private key en lugar seguro
- [ ] Empezar con <10% del capital total
- [ ] Monitoreo activo primeras 24h

---

## 🚀 Próximos Pasos

Después de dominar FASE 1:

1. **FASE 2** - NewsAPI + Technical Indicators (+30% ROI)
2. **Backtest completo** - 6 meses de datos
3. **Scaling** - Aumentar capital gradualmente
4. **Diversificación** - Múltiples mercados simultáneos
5. **Automatización completa** - VPS 24/7

---

**¿Preguntas? ¿Problemas?**

Abrir issue en GitHub: https://github.com/juankaspain/BotPolyMarket/issues/new

---

**Happy Trading! 🚀**
