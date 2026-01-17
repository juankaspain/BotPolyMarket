# 🚀 Despliegue en Producción

Guía completa para desplegar el bot de copy trading en un servidor de producción.

## 📋 Índice

1. [Opciones de Hosting](#opciones-de-hosting)
2. [Configuración de VPS](#configuración-de-vps)
3. [Instalación y Setup](#instalación-y-setup)
4. [Gestión de Procesos](#gestión-de-procesos)
5. [Monitoreo y Alertas](#monitoreo-y-alertas)
6. [Backup y Recuperación](#backup-y-recuperación)
7. [Seguridad](#seguridad)
8. [Mantenimiento](#mantenimiento)

---

## 1. Opciones de Hosting

### Opción A: VPS (Recomendado)

**Proveedores sugeridos:**

| Proveedor | Precio/mes | RAM | vCPU | Pros |
|-----------|------------|-----|------|------|
| **DigitalOcean** | $6-12 | 1-2GB | 1 | Fácil uso, buen soporte |
| **AWS Lightsail** | $3.50-10 | 512MB-2GB | 1-2 | Integración AWS |
| **Linode** | $5-10 | 1-2GB | 1 | Rendimiento estable |
| **Hetzner** | €4-8 | 2-4GB | 2 | Mejor relación precio/calidad |
| **Contabo** | €5 | 8GB | 4 | Mucho RAM, barato |

**Requisitos mínimos:**
- RAM: 1GB (2GB recomendado)
- CPU: 1 vCore
- Disco: 20GB SSD
- OS: Ubuntu 22.04 LTS
- Uptime: 99.9%

### Opción B: Cloud Functions (Para usuarios avanzados)

- **AWS Lambda** + EventBridge
- **Google Cloud Functions**
- **Azure Functions**

⚠️ **Nota:** Cloud Functions requieren adaptación del código.

### Opción C: Raspberry Pi (Para testing)

- **Ventajas:** Bajo costo energético
- **Desventajas:** Sin garantía de uptime, menos potente

---

## 2. Configuración de VPS

### 2.1. Crear y Acceder al VPS

#### DigitalOcean (Ejemplo)

1. Crea un Droplet en DigitalOcean
2. Elige: **Ubuntu 22.04 LTS**
3. Plan: **Basic ($6/mes - 1GB RAM)**
4. Datacenter: Elige el más cercano
5. Autenticación: **SSH Key** (más seguro)

```bash
# Conectar por SSH
ssh root@tu_ip_del_servidor
```

### 2.2. Configuración Inicial del Servidor

```bash
# Actualizar sistema
apt update && apt upgrade -y

# Instalar dependencias básicas
apt install -y python3.11 python3-pip git ufw fail2ban htop

# Crear usuario no-root
adduser botuser
usermod -aG sudo botuser

# Configurar firewall
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

### 2.3. Cambiar a Usuario No-Root

```bash
# Cambiar a usuario botuser
su - botuser

# Generar SSH key para GitHub
ssh-keygen -t ed25519 -C "tu_email@example.com"

# Copiar la clave pública y añadirla en GitHub
cat ~/.ssh/id_ed25519.pub
```

---

## 3. Instalación y Setup

### 3.1. Clonar el Repositorio

```bash
# Clonar repo
cd ~
git clone git@github.com:juankaspain/BotPolyMarket.git
cd BotPolyMarket
```

### 3.2. Crear Entorno Virtual

```bash
# Crear venv
python3 -m venv venv

# Activar venv
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.3. Configurar Variables de Entorno

```bash
# Copiar ejemplo
cp .env.example .env

# Editar con nano o vim
nano .env
```

**Configuración mínima:**

```bash
MODE=execute
PRIVATE_KEY=tu_private_key_sin_0x
TRADER_ADDRESS=0xdireccion_del_trader_a_copiar
YOUR_CAPITAL=100.00

# Seguridad
DRY_RUN_MODE=false
MAX_POSITION_SIZE_PCT=0.05
MAX_DAILY_LOSS_PCT=0.02

# Menú interactivo
USE_INTERACTIVE_MENU=true

# Logging
LOG_LEVEL=INFO
LOG_FILE=bot_polymarket.log
```

### 3.4. Test Inicial

```bash
# Test con DRY_RUN
python main.py

# Si todo funciona, Ctrl+C para detener
```

---

## 4. Gestión de Procesos

### Opción A: systemd (Recomendado)

Crear servicio systemd para que el bot se ejecute automáticamente:

```bash
# Crear archivo de servicio
sudo nano /etc/systemd/system/polymarket-bot.service
```

**Contenido del archivo:**

```ini
[Unit]
Description=Polymarket Copy Trading Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/home/botuser/BotPolyMarket
Environment="PATH=/home/botuser/BotPolyMarket/venv/bin"
ExecStart=/home/botuser/BotPolyMarket/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=append:/home/botuser/BotPolyMarket/logs/bot.log
StandardError=append:/home/botuser/BotPolyMarket/logs/bot-error.log

[Install]
WantedBy=multi-user.target
```

```bash
# Crear directorio de logs
mkdir -p ~/BotPolyMarket/logs

# Recargar systemd
sudo systemctl daemon-reload

# Habilitar inicio automático
sudo systemctl enable polymarket-bot

# Iniciar servicio
sudo systemctl start polymarket-bot

# Ver estado
sudo systemctl status polymarket-bot

# Ver logs en tiempo real
journalctl -u polymarket-bot -f
```

**Comandos útiles:**

```bash
# Detener bot
sudo systemctl stop polymarket-bot

# Reiniciar bot
sudo systemctl restart polymarket-bot

# Ver logs
journalctl -u polymarket-bot --since today
```

### Opción B: PM2 (Alternativa)

```bash
# Instalar PM2
sudo npm install -g pm2

# Iniciar bot
cd ~/BotPolyMarket
source venv/bin/activate
pm2 start main.py --interpreter python3 --name polymarket-bot

# Configurar inicio automático
pm2 startup
pm2 save

# Comandos útiles
pm2 list
pm2 logs polymarket-bot
pm2 restart polymarket-bot
pm2 stop polymarket-bot
```

---

## 5. Monitoreo y Alertas

### 5.1. Monitoreo de Logs

```bash
# Ver logs en tiempo real
tail -f ~/BotPolyMarket/bot_polymarket.log

# Filtrar errores
grep "ERROR" ~/BotPolyMarket/bot_polymarket.log

# Ver últimas 100 líneas
tail -n 100 ~/BotPolyMarket/bot_polymarket.log
```

### 5.2. Script de Monitoreo Automático

Crear `~/BotPolyMarket/scripts/monitor.sh`:

```bash
#!/bin/bash

LOG_FILE="/home/botuser/BotPolyMarket/bot_polymarket.log"
ALERT_EMAIL="tu_email@example.com"

# Verificar si el bot está corriendo
if ! systemctl is-active --quiet polymarket-bot; then
    echo "Bot detenido!" | mail -s "Alerta: Bot Polymarket detenido" $ALERT_EMAIL
    sudo systemctl start polymarket-bot
fi

# Verificar errores recientes
ERROR_COUNT=$(grep -c "ERROR" $LOG_FILE | tail -n 100)
if [ $ERROR_COUNT -gt 10 ]; then
    echo "Más de 10 errores en los últimos logs" | mail -s "Alerta: Errores en bot" $ALERT_EMAIL
fi
```

```bash
# Hacer ejecutable
chmod +x ~/BotPolyMarket/scripts/monitor.sh

# Agregar a crontab (cada 5 minutos)
crontab -e

# Agregar esta línea:
*/5 * * * * /home/botuser/BotPolyMarket/scripts/monitor.sh
```

### 5.3. Alertas por Telegram (Opcional)

Instalar bot de Telegram para alertas:

```bash
pip install python-telegram-bot
```

Crear `~/BotPolyMarket/utils/telegram_alerts.py`:

```python
import os
import requests

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=data)
```

Añadir al `.env`:
```bash
TELEGRAM_BOT_TOKEN=tu_token_aqui
TELEGRAM_CHAT_ID=tu_chat_id
```

### 5.4. Dashboard de Monitoreo (Avanzado)

**Grafana + Prometheus:**

```bash
# Instalar Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.linux-amd64.tar.gz
tar xvfz prometheus-*.tar.gz
cd prometheus-*

# Configurar y ejecutar
./prometheus --config.file=prometheus.yml
```

---

## 6. Backup y Recuperación

### 6.1. Backup de Base de Datos

Script de backup automático `~/BotPolyMarket/scripts/backup.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/home/botuser/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_FILE="/home/botuser/BotPolyMarket/bot_polymarket.db"

# Crear directorio de backup
mkdir -p $BACKUP_DIR

# Backup de base de datos
cp $DB_FILE $BACKUP_DIR/bot_db_$DATE.db

# Backup de .env
cp /home/botuser/BotPolyMarket/.env $BACKUP_DIR/.env_$DATE

# Backup de logs
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz /home/botuser/BotPolyMarket/logs/

# Mantener solo los últimos 30 días
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completado: $DATE"
```

```bash
# Hacer ejecutable
chmod +x ~/BotPolyMarket/scripts/backup.sh

# Agregar a crontab (backup diario a las 3 AM)
crontab -e
0 3 * * * /home/botuser/BotPolyMarket/scripts/backup.sh
```

### 6.2. Backup en la Nube

**Opción A: AWS S3**

```bash
# Instalar AWS CLI
sudo apt install -y awscli

# Configurar
aws configure

# Subir backup
aws s3 cp $BACKUP_DIR/bot_db_$DATE.db s3://tu-bucket/backups/
```

**Opción B: Dropbox**

```bash
pip install dropbox
```

### 6.3. Restaurar desde Backup

```bash
# Detener bot
sudo systemctl stop polymarket-bot

# Restaurar base de datos
cp /home/botuser/backups/bot_db_20260117_030000.db /home/botuser/BotPolyMarket/bot_polymarket.db

# Reiniciar bot
sudo systemctl start polymarket-bot
```

---

## 7. Seguridad

### 7.1. Firewall (UFW)

```bash
# Ver estado
sudo ufw status

# Permitir solo SSH
sudo ufw allow 22/tcp

# Denegar todo lo demás
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Habilitar
sudo ufw enable
```

### 7.2. Fail2Ban (Protección contra ataques)

```bash
# Instalar
sudo apt install fail2ban

# Configurar
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo nano /etc/fail2ban/jail.local
```

Configurar SSH jail:
```ini
[sshd]
enabled = true
port = 22
maxretry = 3
bantime = 3600
```

```bash
# Reiniciar
sudo systemctl restart fail2ban
```

### 7.3. Actualizaciones Automáticas

```bash
# Instalar unattended-upgrades
sudo apt install unattended-upgrades

# Configurar
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 7.4. Protección de Private Key

```bash
# Permisos correctos para .env
chmod 600 ~/.BotPolyMarket/.env

# Verificar que .env esté en .gitignore
grep ".env" ~/BotPolyMarket/.gitignore
```

---

## 8. Mantenimiento

### 8.1. Actualización del Bot

```bash
# Detener bot
sudo systemctl stop polymarket-bot

# Actualizar código
cd ~/BotPolyMarket
git pull origin main

# Actualizar dependencias
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Reiniciar
sudo systemctl start polymarket-bot
```

### 8.2. Rotación de Logs

Crear `/etc/logrotate.d/polymarket-bot`:

```bash
/home/botuser/BotPolyMarket/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 botuser botuser
}
```

### 8.3. Limpieza de Espacio

```bash
# Ver uso de disco
df -h

# Limpiar logs antiguos
sudo journalctl --vacuum-time=7d

# Limpiar apt cache
sudo apt clean

# Eliminar paquetes innecesarios
sudo apt autoremove
```

### 8.4. Monitoreo de Rendimiento

```bash
# Ver uso de CPU/RAM
htop

# Ver uso del bot específicamente
top -p $(pgrep -f "python main.py")

# Espacio en disco
du -sh ~/BotPolyMarket/*
```

---

## 🎯 Checklist de Producción

Antes de poner en producción, verificar:

- [ ] VPS configurado y securizado
- [ ] Firewall (UFW) habilitado
- [ ] Fail2Ban configurado
- [ ] Bot corriendo como servicio systemd
- [ ] Backups automáticos configurados
- [ ] Monitoreo y alertas activadas
- [ ] Variables de entorno configuradas correctamente
- [ ] Private key segura (nunca en Git)
- [ ] DRY_RUN_MODE testeado primero
- [ ] Límites de seguridad configurados
- [ ] Logs funcionando correctamente
- [ ] Script de actualización preparado

---

## 👁️ Comandos Rápidos de Referencia

```bash
# Estado del bot
sudo systemctl status polymarket-bot

# Reiniciar bot
sudo systemctl restart polymarket-bot

# Ver logs en tiempo real
journalctl -u polymarket-bot -f

# Ver logs del día
journalctl -u polymarket-bot --since today

# Ver uso de recursos
htop

# Backup manual
~/BotPolyMarket/scripts/backup.sh

# Actualizar bot
cd ~/BotPolyMarket && git pull && sudo systemctl restart polymarket-bot
```

---

## 📞 Soporte y Troubleshooting

### Bot no inicia

1. Verificar logs: `journalctl -u polymarket-bot -n 50`
2. Verificar .env: `nano ~/BotPolyMarket/.env`
3. Test manual: `cd ~/BotPolyMarket && source venv/bin/activate && python main.py`

### Sin conexión a Polymarket

1. Verificar conectividad: `curl https://polymarket.com`
2. Verificar firewall: `sudo ufw status`
3. Ver logs de red: `journalctl -u polymarket-bot | grep "connection"`

### Pérdidas inesperadas

1. Revisar límites: `cat ~/BotPolyMarket/.env | grep MAX_`
2. Ver trades ejecutados: `grep "Trade ejecutado" ~/BotPolyMarket/bot_polymarket.log`
3. Verificar risk_manager: `grep "RiskManager" ~/BotPolyMarket/bot_polymarket.log`

---

## 📄 Recursos Adicionales

- **DigitalOcean Tutorials:** https://www.digitalocean.com/community/tutorials
- **Ubuntu Server Guide:** https://ubuntu.com/server/docs
- **systemd Documentation:** https://www.freedesktop.org/software/systemd/man/
- **Polymarket Docs:** https://docs.polymarket.com/

---

**¡Listo para producción! 🚀**

Recuerda: Empieza con cantidades pequeñas y monitorea constantemente los primeros días.
