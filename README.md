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



## 🏛️ Arquitectura del Bot

El bot está estructurado de forma modular y profesional:

### Componentes Principales

- **Config**: Clase centralizada para toda la configuración
  - Valida variables de entorno al iniciar
  - Proporciona valores por defecto seguros
  - Fácil de extender para nuevas configuraciones

- **PolymarketClient**: Cliente HTTP robusto
  - Estrategia de reintentos automáticos
  - Manejo completo de errores de red
  - Timeouts configurables
  - Logging detallado de peticiones

- **CopyTradingBot**: Lógica principal del bot
  - Detección de nuevas posiciones
  - Tracking de cambios en el portafolio
  - Alertas visuales con emojis
  - Separación clara entre monitoreo y ejecución

### Sistema de Logging

- Doble salida: consola + archivo
- Niveles configurables (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Formato estructurado con timestamps
- Rotación automática de logs (pendiente)

### Gestión de Errores

- Captura de excepciones específicas de red
- Reintentos automáticos con backoff exponencial
- Logs detallados con stack traces
- El bot nunca se detiene por un error puntual

---

## 🚀 Despliegue en Producción

### Opción 1: VPS / Servidor Cloud

```bash
# 1. Conectar al servidor
ssh usuario@tu-servidor.com

# 2. Clonar el repositorio
git clone https://github.com/juankaspain/BotPolyMarket.git
cd BotPolyMarket

# 3. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Configurar variables de entorno
cp .env.example .env
nano .env  # Editar con tus valores

# 6. Ejecutar con systemd (recomendado)
sudo nano /etc/systemd/system/botpolymarket.service
```

**Archivo systemd service:**
```ini
[Unit]
Description=Bot de Copy Trading para Polymarket
After=network.target

[Service]
Type=simple
User=tu-usuario
WorkingDirectory=/home/tu-usuario/BotPolyMarket
Environment="PATH=/home/tu-usuario/BotPolyMarket/venv/bin"
ExecStart=/home/tu-usuario/BotPolyMarket/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Activar y arrancar el servicio
sudo systemctl daemon-reload
sudo systemctl enable botpolymarket
sudo systemctl start botpolymarket

# Ver logs
sudo journalctl -u botpolymarket -f
```

### Opción 2: Docker (próximamente)

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

### Opción 3: Screen/Tmux (desarrollo)

```bash
# Crear sesión persistente
screen -S polymarket-bot
python main.py
# Ctrl+A, D para desconectar

# Reconectar
screen -r polymarket-bot
```

---

## 📊 Monitorización

### Logs

El bot genera logs detallados en `bot_polymarket.log` (por defecto):

```bash
# Ver logs en tiempo real
tail -f bot_polymarket.log

# Buscar errores
grep ERROR bot_polymarket.log

# Últimas 100 líneas
tail -n 100 bot_polymarket.log
```

### Métricas Clave

- **Posiciones activas detectadas**: Número de posiciones del trader objetivo
- **Nuevas posiciones**: Alertas cuando se detectan nuevos trades
- **Errores de API**: Problemas de conexión con Polymarket
- **Uptime**: Tiempo que el bot lleva ejecutándose

---

## 🔧 Troubleshooting

### El bot no arranca

```bash
# Verificar Python
python --version  # Debe ser 3.8+

# Verificar dependencias
pip list

# Reinstalar dependencias
pip install --force-reinstall -r requirements.txt
```

### Error "TRADER_ADDRESS no configurada"

```bash
# Verifica que el archivo .env existe
ls -la .env

# Verifica el contenido (sin mostrar valores sensibles)
grep TRADER_ADDRESS .env
```

### Error de conexión a Polymarket API

- Verifica tu conexión a internet
- Polymarket API puede tener límites de rate
- Aumenta `POLLING_INTERVAL` a 60 segundos o más

### El bot se detiene solo

```bash
# Ver errores recientes
tail -n 50 bot_polymarket.log | grep ERROR

# Usar systemd para auto-restart (ver sección Despliegue)
```

---

## 📦 Actualizaciones

```bash
# Detener el bot
sudo systemctl stop botpolymarket  # Si usas systemd
# O Ctrl+C si está en terminal

# Actualizar código
git pull origin main

# Actualizar dependencias
pip install -r requirements.txt --upgrade

# Reiniciar
sudo systemctl start botpolymarket
```

---

Este bot es solo para fines educativos. El trading conlleva riesgos y puedes perder todo tu capital. No somos responsables de pérdidas financieras derivadas del uso de este software.

## 📞 Soporte

¿Problemas o preguntas? Abre un [Issue](https://github.com/juankaspain/BotPolyMarket/issues)

---

**Made with ❤️ by [@juankaspain](https://github.com/juankaspain)**
