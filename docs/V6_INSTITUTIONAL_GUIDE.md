# v6.0 Institutional Platform - Documentation

## 🏛️ Overview

Plataforma institucional con API profesional, KYC compliance, copy trading y white-label para escalar a 1M€ AUM.

## 🚀 Quick Start

### API Installation

```bash
# Instalar dependencias
pip install fastapi uvicorn pyjwt redis slowapi

# Lanzar API
python api/institutional_api.py
```

### API Endpoint

- **URL:** http://localhost:8000
- **Docs:** http://localhost:8000/docs (Swagger UI)
- **Health:** http://localhost:8000/api/v1/health

## 🔑 Authentication

### Login

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -d "username=demo&password=demo123"
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Using Token

```bash
curl -X POST "http://localhost:8000/api/v1/signals/custom" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

## 📡 Custom Signals API (+30% Benefit)

### Submit Trading Signal

```python
import requests

url = "http://localhost:8000/api/v1/signals/custom"
headers = {"Authorization": "Bearer YOUR_TOKEN"}

signal = {
    "market_id": "crypto-btc-100k-2026",
    "side": "YES",
    "confidence": 0.85,
    "size": 1000,
    "max_price": 0.65,
    "strategy": "institutional_ml"
}

response = requests.post(url, json=signal, headers=headers)
print(response.json())
```

**Response:**
```json
{
  "signal_id": "signal_123",
  "status": "executed",
  "expected_profit": 300.0,
  "execution_time": "2026-06-01T10:30:00"
}
```

## 👥 Copy Trading API (+50% Benefit)

### Configure Copy Group

```python
url = "http://localhost:8000/api/v1/copy-trading/configure"

config = {
    "master_wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    "follower_wallets": [
        "0xabc...",
        "0xdef...",
        # ... hasta 100 wallets
    ],
    "copy_ratio": 1.0,
    "max_position_size": 5000,
    "enabled": true
}

response = requests.post(url, json=config, headers=headers)
```

**Features:**
- Soporte hasta 100 wallets simultáneas
- Ratio configurable (0.1x - 2.0x)
- Límites de posición por wallet
- Enable/disable instantáneo

## 📝 KYC Compliance (EU Madrid)

### Submit KYC

```python
url = "http://localhost:8000/api/v1/kyc/submit"

kyc_data = {
    "user_id": "user_12345",
    "full_name": "Juan García",
    "email": "juan@example.com",
    "country": "ES",
    "document_type": "DNI",
    "document_number": "12345678A",
    "document_url": "https://storage.example.com/doc.pdf"
}

response = requests.post(url, json=kyc_data)
```

### Check KYC Status

```python
url = f"http://localhost:8000/api/v1/kyc/status/{user_id}"
response = requests.get(url, headers=headers)

print(response.json())
# {
#   "status": "approved",
#   "verified_at": "2026-05-15T14:30:00",
#   "compliance_level": "FULL"
# }
```

**Supported Countries:** ES, FR, DE, IT, PT, NL, BE

## 🏷️ White-Label VPS (Revenue Stream)

### Provision Instance

```python
url = "http://localhost:8000/api/v1/white-label/provision"

config = {
    "client_id": "enterprise_corp",
    "domain": "trading.enterprise.com",
    "branding": {
        "logo_url": "https://...",
        "primary_color": "#0066cc",
        "company_name": "Enterprise Trading"
    }
}

response = requests.post(url, json=config, headers=headers)
```

**Response:**
```json
{
  "instance_id": "vps_101",
  "domain": "trading.enterprise.com",
  "api_endpoint": "https://trading.enterprise.com/api",
  "dashboard_url": "https://trading.enterprise.com/dashboard",
  "status": "provisioning",
  "estimated_time": "10-15 minutes",
  "monthly_fee": 500
}
```

**Pricing:**
- Setup fee: €1,000 (one-time)
- Monthly: €500/instance
- Custom branding included
- Dedicated VPS resources

## 📊 AUM Statistics

### Get AUM Stats

```python
url = "http://localhost:8000/api/v1/stats/aum"
response = requests.get(url, headers=headers)

print(response.json())
# {
#   "total_aum": 750000,
#   "target_aum": 1000000,
#   "progress": 0.75,
#   "num_clients": 50,
#   "avg_account_size": 15000,
#   "roi_ytd": 2.0
# }
```

**Metas v6.0:**
- AUM Target: 1M€
- ROI Target: +200%
- Clients: 50-100
- Avg Size: 10-20k€

## 🔒 Rate Limiting

### Tiers

| Tier | Requests/min | Monthly | AUM Required |
|------|--------------|---------|---------------|
| Free | 10 | €0 | - |
| Basic | 100 | €50 | 1k€ |
| Pro | 1,000 | €200 | 10k€ |
| Institutional | 10,000 | €1,000 | 100k€ |

### Headers

Cada response incluye:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 45
```

## 🐳 Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.institutional_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - redis
      - postgres
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

## 🔗 Integration Examples

### Python SDK

```python
from botpolymarket import InstitutionalClient

client = InstitutionalClient(
    api_key="your_key",
    api_url="https://api.botpolymarket.com"
)

# Submit signal
result = client.submit_signal(
    market_id="btc-100k",
    side="YES",
    confidence=0.85,
    size=1000
)

# Configure copy trading
client.setup_copy_trading(
    master="0x...",
    followers=["0x...", "0x..."]
)

# Check AUM
aum = client.get_aum_stats()
print(f"Total AUM: €{aum['total_aum']:,}")
```

### JavaScript SDK

```javascript
const { InstitutionalClient } = require('@botpolymarket/sdk');

const client = new InstitutionalClient({
  apiKey: 'your_key',
  apiUrl: 'https://api.botpolymarket.com'
});

// Submit signal
const result = await client.submitSignal({
  marketId: 'btc-100k',
  side: 'YES',
  confidence: 0.85,
  size: 1000
});

console.log('Signal executed:', result);
```

## 🎯 Success Metrics

**Launch Targets (Jun 2026):**
- ✅ 1M€ AUM
- ✅ +200% ROI
- ✅ 50+ institutional clients
- ✅ 10+ white-label instances
- ✅ EU compliance (Madrid)

**Revenue Streams:**
1. Management fees: 2% annual
2. Performance fees: 20% profits
3. White-label: €500/mo per instance
4. API access: €50-1000/mo tiers

## 📞 Support

**Enterprise Support:**
- Email: enterprise@botpolymarket.com
- Slack: enterprise.slack.com
- Phone: +34 xxx xxx xxx (Madrid)

**Documentation:**
- API Docs: https://docs.botpolymarket.com
- SDK: https://github.com/juankaspain/botpolymarket-sdk

---

**v6.0 Institutional Platform** | Junio 2026 | BotPolyMarket
