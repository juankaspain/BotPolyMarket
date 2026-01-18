# BotPolyMarket - Production Deployment Guide

## 🎯 Overview

Guía completa para desplegar BotPolyMarket en producción desde v2.0 hasta v6.0.

## 💻 System Requirements

### Hardware (VPS)

**Minimum:**
- CPU: 4 cores
- RAM: 8 GB
- Storage: 100 GB SSD
- Network: 100 Mbps

**Recommended (v6.0):**
- CPU: 8 cores
- RAM: 16 GB
- Storage: 500 GB NVMe SSD
- Network: 1 Gbps

### Software

- Ubuntu 22.04 LTS
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker 24+
- Nginx 1.24+

## 🚀 Quick Deploy

### 1. Clone Repository

```bash
ssh user@your-vps
cd /opt
git clone https://github.com/juankaspain/BotPolyMarket.git
cd BotPolyMarket
```

### 2. Setup Environment

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
nano .env
```

**Required variables:**

```bash
# Trading
TRADING_MODE=live  # or 'paper'
POLYMARKET_API_KEY=your_key
POLYMARKET_PRIVATE_KEY=your_private_key

# Database
DATABASE_URL=postgresql://user:pass@localhost/botpolymarket
REDIS_URL=redis://localhost:6379

# ML Models
ML_MODEL_PATH=/opt/BotPolyMarket/models/lstm_gap_predictor_v2.0.h5

# Telegram
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id

# DeFi (v5.0)
POLYGON_RPC=https://polygon-rpc.com
BASE_RPC=https://mainnet.base.org
WALLET_PRIVATE_KEY=your_defi_key

# API (v6.0)
SECRET_KEY=your_jwt_secret
API_RATE_LIMIT=100
```

### 4. Initialize Database

```bash
# Create database
sudo -u postgres psql
CREATE DATABASE botpolymarket;
CREATE USER botuser WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE botpolymarket TO botuser;
\q

# Run migrations
alembic upgrade head
```

### 5. Start Services

```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Or manually
python main.py &
python core/institutional_api.py &
streamlit run dashboard/streamlit_app.py &
```

## 🐳 Docker Deployment

### Build Images

```bash
# Main bot
docker build -t botpolymarket:latest .

# Dashboard
docker build -t botpolymarket-dashboard:latest -f Dockerfile.dashboard .

# API
docker build -t botpolymarket-api:latest -f Dockerfile.api .
```

### Docker Compose

```yaml
version: '3.8'

services:
  bot:
    image: botpolymarket:latest
    restart: always
    env_file: .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./models:/app/models
    depends_on:
      - postgres
      - redis
  
  dashboard:
    image: botpolymarket-dashboard:latest
    restart: always
    ports:
      - "8501:8501"
    env_file: .env
    depends_on:
      - bot
  
  api:
    image: botpolymarket-api:latest
    restart: always
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - bot
  
  postgres:
    image: postgres:15
    restart: always
    environment:
      POSTGRES_DB: botpolymarket
      POSTGRES_USER: botuser
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    restart: always
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Run

```bash
docker-compose up -d

# Check logs
docker-compose logs -f bot
```

## 🔒 Security Hardening

### 1. Firewall

```bash
# UFW
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### 2. SSL Certificate

```bash
# Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.botpolymarket.com
sudo certbot --nginx -d dashboard.botpolymarket.com
```

### 3. Nginx Configuration

```nginx
# /etc/nginx/sites-available/botpolymarket

# API
server {
    listen 443 ssl http2;
    server_name api.botpolymarket.com;
    
    ssl_certificate /etc/letsencrypt/live/api.botpolymarket.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.botpolymarket.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Dashboard
server {
    listen 443 ssl http2;
    server_name dashboard.botpolymarket.com;
    
    ssl_certificate /etc/letsencrypt/live/dashboard.botpolymarket.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dashboard.botpolymarket.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

### 4. Systemd Services

```ini
# /etc/systemd/system/botpolymarket.service

[Unit]
Description=BotPolyMarket Trading Bot
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=botuser
WorkingDirectory=/opt/BotPolyMarket
Environment="PATH=/opt/BotPolyMarket/venv/bin"
ExecStart=/opt/BotPolyMarket/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable botpolymarket
sudo systemctl start botpolymarket
sudo systemctl status botpolymarket
```

## 📊 Monitoring

### 1. Prometheus + Grafana

```yaml
# docker-compose.monitoring.yml

services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

### 2. Logs

```bash
# Centralized logging
sudo apt install rsyslog

# Rotate logs
sudo nano /etc/logrotate.d/botpolymarket
```

```
/opt/BotPolyMarket/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 botuser botuser
}
```

### 3. Alerts

```python
# Configure Telegram alerts
from core.telegram_notifier import TelegramNotifier

notifier = TelegramNotifier()
await notifier.send_alert(
    "⚠️ Bot stopped!",
    severity="critical"
)
```

## 🔄 Backup & Recovery

### Database Backup

```bash
# Daily backup cron
0 2 * * * pg_dump botpolymarket | gzip > /backups/db_$(date +\%Y\%m\%d).sql.gz
```

### Models Backup

```bash
# Backup trained models
rsync -avz /opt/BotPolyMarket/models/ user@backup-server:/backups/models/
```

## 💰 Cost Estimation

### VPS (Hetzner/DigitalOcean)

```
CPX41 (8 vCPU, 16GB RAM): €30/month
Storage 500GB: €10/month
Backup: €5/month
========================
Total: €45/month = €540/year
```

### Additional Services

```
Domain: €12/year
SSL: Free (Let's Encrypt)
Monitoring: €0 (self-hosted)
Databases: Included
========================
Total: €552/year
```

## ✅ Production Checklist

- [ ] Environment variables configured
- [ ] Database initialized
- [ ] SSL certificates installed
- [ ] Firewall configured
- [ ] Backups automated
- [ ] Monitoring active
- [ ] Logs rotation configured
- [ ] Systemd services enabled
- [ ] Telegram alerts working
- [ ] API rate limiting active
- [ ] Multi-sig wallet configured (v5.0)
- [ ] KYC integration tested (v6.0)

## 📞 Support

**Issues:** https://github.com/juankaspain/BotPolyMarket/issues

---

**Production Deployment Guide** | BotPolyMarket v2.0-v6.0
