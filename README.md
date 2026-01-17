# 🤖 BotPolyMarket - Copy Trading Bot

Bot automatizado para monitorizar y replicar trades de traders exitosos en Polymarket.

## 📊 Características

- ✅ Monitorización 24/7 de traders seleccionados
- ✅ Detección automática de nuevas posiciones
- ✅ Visualización en tiempo real del portafolio
- ✅ Calculadora de tamaño proporcional de posiciones
- ✅ Modo monitor (sin ejecutar trades reales)
- ⚠️ Modo execute (requiere configuración adicional de wallet)

## 🚀 Instalación Rápida

### Requisitos
- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### Pasos

1. **Clonar el repositorio**
```bash
git clone https://github.com/juankaspain/BotPolyMarket.git
cd BotPolyMarket
```

2. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

3. **Configurar la dirección del trader**

Edita `main.py` y pega la dirección wallet del trader que quieres copiar:

```python
TRADER_ADDRESS = "0x..."  # Pegar aquí la dirección
YOUR_CAPITAL = 1000  # Tu capital disponible en USD
```

4. **Ejecutar el bot**
```bash
python main.py
```

## 🛠️ Configuración

El bot se puede configurar editando las variables al inicio de `main.py`:

```python
TRADER_ADDRESS = ""       # Dirección wallet del trader a copiar
YOUR_CAPITAL = 1000      # Tu capital disponible (USD)
POLLING_INTERVAL = 30    # Segundos entre verificaciones
MODE = "monitor"         # "monitor" o "execute"
```

### Modos de Operación

- **monitor**: Solo monitoriza y muestra las posiciones sin ejecutar trades
- **execute**: Ejecuta trades reales (requiere configuración de wallet - NO IMPLEMENTADO)

## 👀 Cómo Obtener la Dirección de un Trader

1. Ve al perfil del trader en Polymarket (ej: https://polymarket.com/@kch123)
2. Haz clic en el icono de compartir 🔗 junto al avatar
3. La dirección wallet se copiará automáticamente al portapapeles
4. Pégala en la variable `TRADER_ADDRESS` en `main.py`

## 📝 Ejemplo de Uso

```bash
$ python main.py

╔══════════════════════════════════════════════════════════╗
║     BOT DE COPY TRADING - POLYMARKET                     ║
║     Monitoriza traders exitosos automáticamente          ║
╚══════════════════════════════════════════════════════════╝

🎯 Trader objetivo: 0x1234...5678
💰 Capital: $1,000.00
⏱️  Intervalo: 30s
🔧 Modo: MONITOR
────────────────────────────────────────────────────────────

🔄 Iteración #1 - 2026-01-17 03:00:00
📊 Posiciones activas: 8

🏆 Top 5 posiciones por valor:
📈 1. Will SV Werder Bremen win on 2026-01-16?
   └─ No | $800,000.00 | PnL: +61.29%
📈 2. Spread: Arkansas State Red Wolves (-4.5)
   └─ South Alabama Jaguars | $399,800.00 | PnL: +103.98%
...
```

## ⚠️ Advertencias Importantes

- **🚫 NO compartas tu private key**: Este bot en modo monitor NO requiere tu private key
- **💸 Gestión de riesgo**: El copy trading no garantiza rentabilidad
- **⏱️ Latencia**: Siempre habrá un retraso entre la acción del trader y tu replicación
- **📉 Slippage**: Los precios pueden cambiar entre la detección y la ejecución
- **📚 Educación**: Entiende los mercados antes de operar con dinero real

## 📄 Licencia

MIT License - Ver archivo LICENSE para más detalles

## 👥 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## ℹ️ Disclaimer

Este bot es solo para fines educativos. El trading conlleva riesgos y puedes perder todo tu capital. No somos responsables de pérdidas financieras derivadas del uso de este software.

## 📞 Soporte

¿Problemas o preguntas? Abre un [Issue](https://github.com/juankaspain/BotPolyMarket/issues)

---

**Made with ❤️ by [@juankaspain](https://github.com/juankaspain)**
