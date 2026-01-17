# 🚀 Modo Execute - Guía Completa

## ⚠️ ADVERTENCIA CRÍTICA

**Este modo ejecuta trades REALES con dinero REAL en Polymarket.**

- ❌ NUNCA uses tu private key principal
- ✅ Crea una wallet nueva específica para el bot
- ✅ Empieza con cantidades pequeñas ($10-$50)
- ✅ Prueba primero en testnet si está disponible
- ✅ Usa DRY_RUN_MODE=true para simulaciones

---

## 📋 Requisitos Previos

### 1. Dependencias
```bash
pip install -r requirements.txt
```

### 2. Wallet de Polygon
- **Opción A**: Crear wallet nueva (recomendado)
- **Opción B**: Exportar private key desde MetaMask

⚠️ **IMPORTANTE**: Nunca compartas tu private key ni la subas a Git

### 3. USDC en Polygon
- Necesitas USDC en Polygon Network
- Bridge desde Ethereum u otra chain
- Puente recomendado: https://wallet.polygon.technology/

### 4. MATIC para Gas
- Necesitas MATIC para pagar gas fees
- ~0.1 MATIC es suficiente para empezar

---

## ⚙️ Configuración

### Paso 1: Copiar .env.example
```bash
cp .env.example .env
```

### Paso 2: Configurar Variables Críticas

Edita `.env` con tu editor:

```bash
# ===========================================
# CONFIGURACIÓN EXECUTE MODE
# ===========================================

# Cambiar modo a execute
MODE=execute

# ⚠️ CRÍTICO: Tu private key (sin 0x)
PRIVATE_KEY=tu_private_key_aqui_sin_0x

# Capital inicial
YOUR_CAPITAL=100.00

# Dirección del trader a copiar
TRADER_ADDRESS=0x...

# ===========================================
# LÍMITES DE SEGURIDAD
# ===========================================

# Modo DRY RUN (simula trades sin ejecutar)
DRY_RUN_MODE=true  # Cambiar a false cuando estés listo

# Límites de posición
MAX_POSITION_SIZE_PCT=0.05        # 5% del capital por trade
MAX_POSITION_VALUE_USD=50.00      # Máximo $50 por posición

# Límites de pérdida
MAX_DAILY_LOSS_PCT=0.02           # 2% pérdida máxima diaria
MAX_DRAWDOWN_PCT=0.10             # 10% drawdown máximo

# Límites de exposición
MAX_POSITIONS_TOTAL=5             # Máximo 5 posiciones simultáneas
MAX_POSITIONS_PER_STRATEGY=3      # Máximo 3 por estrategia
```

---

## 🏃 Ejecución

### Modo 1: DRY RUN (Simulación)

**Recomendado para empezar:**

```bash
# Configurar en .env:
# DRY_RUN_MODE=true

python main.py
```

Esto simulará los trades sin ejecutarlos realmente.

### Modo 2: LIVE (Ejecución Real)

**Solo cuando estés 100% seguro:**

```bash
# Configurar en .env:
# DRY_RUN_MODE=false
# Verificar límites de seguridad

python main.py
```

---

## 🛡️ Sistema de Seguridad

### Validaciones Automáticas

El bot valida CADA trade antes de ejecutar:

1. ✅ **Tamaño de posición**
   - No excede MAX_POSITION_SIZE_PCT
   - No excede MAX_POSITION_VALUE_USD

2. ✅ **Límite de posiciones**
   - No excede MAX_POSITIONS_TOTAL
   - No excede MAX_POSITIONS_PER_STRATEGY

3. ✅ **Pérdidas diarias**
   - Detiene trading si se alcanza MAX_DAILY_LOSS_PCT

4. ✅ **Drawdown máximo**
   - Detiene trading si se alcanza MAX_DRAWDOWN_PCT

5. ✅ **Balance de wallet**
   - Verifica saldo suficiente de USDC
   - Verifica saldo suficiente de MATIC para gas

### Logs y Monitoreo

Todos los trades se registran en:
- `bot_polymarket.log` - Log detallado
- Consola - Output en tiempo real

---

## 📊 Ejemplo de Flujo

```
1. Bot detecta nueva posición del trader
   ↓
2. RiskManager valida el trade
   ✓ Tamaño OK
   ✓ Límites OK
   ✓ Balance OK
   ↓
3. WalletManager verifica saldos
   ✓ USDC: $150.00
   ✓ MATIC: 0.5
   ↓
4. TradeExecutor envía orden
   → Orden ID: 0x123...
   ↓
5. Confirmación on-chain
   ✓ Trade ejecutado
   ✓ Posición registrada
```

---

## 🚨 Qué Hacer Si...

### El bot no ejecuta trades

1. Verificar DRY_RUN_MODE=false
2. Verificar saldo de USDC
3. Verificar saldo de MATIC
4. Revisar logs para errores

### Alcanzas límite de pérdida

El bot se detendrá automáticamente.

Para reiniciar:
```bash
# Revisar estrategia
# Ajustar límites si es necesario
# Esperar al día siguiente (se resetea daily_loss)
python main.py
```

### Error "Insufficient balance"

```bash
# Verificar saldos
# Agregar más USDC o MATIC
# Reducir MAX_POSITION_VALUE_USD
```

---

## 📈 Mejores Prácticas

### Para Principiantes

1. ✅ Empieza con $10-$20
2. ✅ Usa DRY_RUN_MODE primero
3. ✅ MAX_POSITION_SIZE_PCT = 0.02 (2%)
4. ✅ MAX_POSITIONS_TOTAL = 3
5. ✅ Monitorea constantemente los primeros días

### Para Usuarios Avanzados

1. ⚡ Capital $500+
2. ⚡ MAX_POSITION_SIZE_PCT = 0.05-0.10
3. ⚡ MAX_POSITIONS_TOTAL = 10
4. ⚡ Trailing stops activados
5. ⚡ Diversificación entre múltiples traders

---

## 🔒 Seguridad de Private Key

### ✅ DO
- Usar wallet nueva específica
- Guardar backup offline
- Usar .env (nunca subir a Git)
- Limitar fondos en la wallet

### ❌ DON'T
- Usar tu wallet principal
- Compartir private key
- Subir .env a GitHub
- Dejar grandes cantidades

---

## 📞 Soporte

### Logs
```bash
tail -f bot_polymarket.log
```

### Issues
Si encuentras bugs o tienes dudas:
- GitHub Issues: https://github.com/juankaspain/BotPolyMarket/issues

### Documentación Polymarket
- CLOB API: https://docs.polymarket.com/
- py-clob-client: https://github.com/Polymarket/py-clob-client

---

## ⚖️ Disclaimer

**Este bot es para uso educacional.**

- Trading automatizado conlleva riesgos
- Puedes perder todo tu capital
- No hay garantía de ganancias
- Usa bajo tu propio riesgo
- No me hago responsable de pérdidas

**Trade responsablemente. 🎯**
