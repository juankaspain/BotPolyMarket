# Multi-Tenancy Guide
**Soporte para Múltiples Usuarios y Cuentas en BotPolyMarket**

## 📋 Tabla de Contenidos

- [Introducción](#introducción)
- [Arquitectura](#arquitectura)
- [Implementación](#implementación)
- [Casos de Uso](#casos-de-uso)
- [Seguridad](#seguridad)
- [Administración](#administración)
- [API Reference](#api-reference)
- [Ejemplos](#ejemplos)

---

## Introducción

### ¿Qué es Multi-Tenancy?

Sistema que permite que **múltiples usuarios (tenants)** compartan la misma instancia del bot con:
- **Aislamiento total** de datos y configuraciones
- **Recursos compartidos** (rate limiters, conexiones)
- **Gestión centralizada** de usuarios
- **Billing y quotas** por tenant

### Beneficios

✅ **Para Administradores:**
- Monetizar el bot como SaaS
- Gestión centralizada
- Economías de escala
- Analytics agregados

✅ **Para Usuarios:**
- Sin infraestructura propia
- Actualizaciones automáticas
- Soporte técnico incluido
- Costos compartidos

---

## Arquitectura

### Modelo de Datos

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import uuid

class TenantTier(Enum):
    """Niveles de subscripción"""
    FREE = "free"          # 100 trades/mes
    BASIC = "basic"        # 1,000 trades/mes
    PRO = "pro"            # 10,000 trades/mes
    ENTERPRISE = "enterprise"  # Unlimited

class TenantStatus(Enum):
    """Estado del tenant"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    EXPIRED = "expired"

@dataclass
class TenantConfig:
    """Configuración por tenant"""
    # Identidad
    tenant_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    email: str = ""
    
    # Subscripción
    tier: TenantTier = TenantTier.FREE
    status: TenantStatus = TenantStatus.TRIAL
    
    # Trading
    capital: float = 1000.0
    max_position_size: float = 100.0
    max_daily_trades: int = 10
    
    # APIs
    polymarket_api_key: Optional[str] = None
    polymarket_private_key: Optional[str] = None
    binance_api_key: Optional[str] = None
    binance_secret: Optional[str] = None
    
    # Estrategias habilitadas
    enabled_strategies: List[str] = field(default_factory=list)
    
    # Rate limits personalizados
    rate_limits: Dict[str, int] = field(default_factory=dict)
    
    # Quotas
    monthly_trades_quota: int = 100
    monthly_trades_used: int = 0
    
    # Metadata
    created_at: str = ""
    updated_at: str = ""
    last_active: str = ""

@dataclass
class TenantMetrics:
    """Métricas por tenant"""
    tenant_id: str
    
    # Trading
    total_trades: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    total_pnl: float = 0.0
    
    # Performance
    win_rate: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    
    # Uso de recursos
    api_calls: int = 0
    compute_time_seconds: float = 0.0
    storage_bytes: int = 0
```

### Arquitectura de Componentes

```
┌─────────────────────────────────────────────────────┐
│                  API Gateway                        │
│           (Authentication & Routing)                │
└────────────────────┬────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
┌────────▼────────┐    ┌────────▼────────┐
│  Tenant Manager │    │  Auth Service   │
│  - Create       │    │  - JWT Tokens   │
│  - Update       │    │  - Permissions  │
│  - Delete       │    │  - API Keys     │
└────────┬────────┘    └─────────────────┘
         │
┌────────▼───────────────────────────────────────────┐
│              Bot Orchestrator                      │
│  ┌──────────────────────────────────────────┐     │
│  │        Per-Tenant Bot Instances          │     │
│  │  ┌──────────┐  ┌──────────┐  ┌────────┐ │     │
│  │  │ Tenant A │  │ Tenant B │  │ Tenant C│ │     │
│  │  │  Bot     │  │  Bot     │  │  Bot    │ │     │
│  │  └──────────┘  └──────────┘  └────────┘ │     │
│  └──────────────────────────────────────────┘     │
└────────────────────────┬───────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
┌────────▼────┐  ┌──────▼──────┐  ┌────▼─────┐
│  Shared     │  │   Shared    │  │  Shared  │
│  Database   │  │ Rate Limiter│  │  Cache   │
└─────────────┘  └─────────────┘  └──────────┘
```

---

## Implementación

### 1. Tenant Manager

**Archivo:** `core/tenant_manager.py`

```python
import json
import logging
import sqlite3
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class TenantManager:
    """Gestor de tenants (multi-usuario)"""
    
    def __init__(self, db_path: str = "data/tenants.db"):
        self.db_path = db_path
        self._init_database()
        self.tenants: Dict[str, TenantConfig] = {}
        self._load_tenants()
        
        logger.info(f"✅ TenantManager initialized with {len(self.tenants)} tenants")
    
    def _init_database(self):
        """Crear base de datos de tenants"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla de tenants
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tenants (
                tenant_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                tier TEXT NOT NULL,
                status TEXT NOT NULL,
                config TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de métricas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tenant_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_trades INTEGER DEFAULT 0,
                successful_trades INTEGER DEFAULT 0,
                total_pnl REAL DEFAULT 0.0,
                FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
            )
        ''')
        
        # Tabla de trades
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tenant_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                market_id TEXT,
                side TEXT,
                amount REAL,
                price REAL,
                pnl REAL,
                status TEXT,
                FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
            )
        ''')
        
        # Índices
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tenant_email ON tenants(email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tenant_status ON tenants(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_tenant ON tenant_trades(tenant_id)')
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Tenant database initialized")
    
    def _load_tenants(self):
        """Cargar tenants desde DB"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT tenant_id, config FROM tenants WHERE status = "active"')
        
        for row in cursor.fetchall():
            tenant_id, config_json = row
            config_dict = json.loads(config_json)
            config = TenantConfig(**config_dict)
            self.tenants[tenant_id] = config
        
        conn.close()
    
    def create_tenant(self, name: str, email: str, tier: TenantTier = TenantTier.FREE) -> TenantConfig:
        """Crear nuevo tenant"""
        # Validar email único
        if self.get_tenant_by_email(email):
            raise ValueError(f"Email {email} already exists")
        
        # Crear config
        config = TenantConfig(
            name=name,
            email=email,
            tier=tier,
            status=TenantStatus.TRIAL,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )
        
        # Guardar en DB
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO tenants (tenant_id, name, email, tier, status, config)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            config.tenant_id,
            config.name,
            config.email,
            config.tier.value,
            config.status.value,
            json.dumps(config.__dict__)
        ))
        
        conn.commit()
        conn.close()
        
        # Agregar a memoria
        self.tenants[config.tenant_id] = config
        
        logger.info(f"✅ Created tenant: {name} ({email}) - {tier.value}")
        return config
    
    def get_tenant(self, tenant_id: str) -> Optional[TenantConfig]:
        """Obtener tenant por ID"""
        return self.tenants.get(tenant_id)
    
    def get_tenant_by_email(self, email: str) -> Optional[TenantConfig]:
        """Obtener tenant por email"""
        for tenant in self.tenants.values():
            if tenant.email == email:
                return tenant
        return None
    
    def update_tenant(self, tenant_id: str, **updates) -> TenantConfig:
        """Actualizar tenant"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        # Actualizar campos
        for key, value in updates.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)
        
        tenant.updated_at = datetime.utcnow().isoformat()
        
        # Guardar en DB
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE tenants 
            SET config = ?, updated_at = CURRENT_TIMESTAMP
            WHERE tenant_id = ?
        ''', (json.dumps(tenant.__dict__), tenant_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Updated tenant {tenant_id}")
        return tenant
    
    def delete_tenant(self, tenant_id: str):
        """Eliminar tenant (soft delete)"""
        self.update_tenant(tenant_id, status=TenantStatus.EXPIRED)
        del self.tenants[tenant_id]
        logger.info(f"✅ Deleted tenant {tenant_id}")
    
    def check_quota(self, tenant_id: str) -> bool:
        """Verificar si tenant tiene quota disponible"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False
        
        # ENTERPRISE: sin límite
        if tenant.tier == TenantTier.ENTERPRISE:
            return True
        
        # Verificar quota mensual
        return tenant.monthly_trades_used < tenant.monthly_trades_quota
    
    def increment_usage(self, tenant_id: str):
        """Incrementar contador de uso"""
        tenant = self.get_tenant(tenant_id)
        if tenant:
            tenant.monthly_trades_used += 1
            self.update_tenant(tenant_id, monthly_trades_used=tenant.monthly_trades_used)
    
    def record_trade(self, tenant_id: str, trade_data: dict):
        """Registrar trade de tenant"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO tenant_trades (
                tenant_id, market_id, side, amount, price, pnl, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            tenant_id,
            trade_data.get('market_id'),
            trade_data.get('side'),
            trade_data.get('amount'),
            trade_data.get('price'),
            trade_data.get('pnl', 0.0),
            trade_data.get('status', 'pending')
        ))
        
        conn.commit()
        conn.close()
        
        # Incrementar uso
        self.increment_usage(tenant_id)
    
    def get_tenant_metrics(self, tenant_id: str) -> TenantMetrics:
        """Obtener métricas de tenant"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total trades
        cursor.execute('''
            SELECT COUNT(*), 
                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END),
                   SUM(pnl)
            FROM tenant_trades
            WHERE tenant_id = ?
        ''', (tenant_id,))
        
        row = cursor.fetchone()
        total_trades, successful, failed, total_pnl = row
        
        conn.close()
        
        # Calcular métricas
        win_rate = (successful / total_trades * 100) if total_trades > 0 else 0.0
        
        return TenantMetrics(
            tenant_id=tenant_id,
            total_trades=total_trades or 0,
            successful_trades=successful or 0,
            failed_trades=failed or 0,
            total_pnl=total_pnl or 0.0,
            win_rate=win_rate
        )
    
    def list_tenants(self, status: Optional[TenantStatus] = None) -> List[TenantConfig]:
        """Listar todos los tenants"""
        if status:
            return [t for t in self.tenants.values() if t.status == status]
        return list(self.tenants.values())
    
    def get_stats(self) -> dict:
        """Estadísticas globales"""
        total = len(self.tenants)
        by_tier = {}
        by_status = {}
        
        for tenant in self.tenants.values():
            by_tier[tenant.tier.value] = by_tier.get(tenant.tier.value, 0) + 1
            by_status[tenant.status.value] = by_status.get(tenant.status.value, 0) + 1
        
        return {
            'total_tenants': total,
            'by_tier': by_tier,
            'by_status': by_status
        }
```

### 2. Multi-Tenant Bot Orchestrator

**Archivo:** `core/multi_tenant_orchestrator.py`

```python
import logging
import threading
from typing import Dict
from concurrent.futures import ThreadPoolExecutor

from core.tenant_manager import TenantManager, TenantConfig
from core.orchestrator import BotOrchestrator

logger = logging.getLogger(__name__)

class MultiTenantOrchestrator:
    """Orquestador para múltiples tenants"""
    
    def __init__(self, max_workers: int = 10):
        self.tenant_manager = TenantManager()
        self.bot_instances: Dict[str, BotOrchestrator] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.running = False
        
        logger.info(f"✅ MultiTenantOrchestrator initialized (max_workers={max_workers})")
    
    def start_tenant_bot(self, tenant_id: str):
        """Iniciar bot para un tenant"""
        tenant = self.tenant_manager.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        # Verificar quota
        if not self.tenant_manager.check_quota(tenant_id):
            logger.warning(f"⚠️ Tenant {tenant_id} exceeded quota")
            return
        
        # Crear configuración de bot
        bot_config = self._create_bot_config(tenant)
        
        # Crear instancia de bot
        bot = BotOrchestrator(bot_config)
        self.bot_instances[tenant_id] = bot
        
        # Ejecutar en thread pool
        self.executor.submit(self._run_tenant_bot, tenant_id, bot)
        
        logger.info(f"✅ Started bot for tenant {tenant.name} ({tenant_id})")
    
    def _create_bot_config(self, tenant: TenantConfig) -> dict:
        """Crear configuración de bot desde tenant config"""
        return {
            'tenant_id': tenant.tenant_id,
            'capital': tenant.capital,
            'mode': 'live' if tenant.tier != TenantTier.FREE else 'paper',
            'private_key': tenant.polymarket_private_key,
            'api_key': tenant.polymarket_api_key,
            'binance_api_key': tenant.binance_api_key,
            'binance_secret': tenant.binance_secret,
            'enabled_strategies': tenant.enabled_strategies,
            'max_position_size': tenant.max_position_size,
            'max_daily_trades': tenant.max_daily_trades,
            'polling_interval': 60
        }
    
    def _run_tenant_bot(self, tenant_id: str, bot: BotOrchestrator):
        """Ejecutar bot de tenant (thread worker)"""
        try:
            logger.info(f"🚀 Running bot for tenant {tenant_id}")
            
            while self.running:
                # Verificar quota
                if not self.tenant_manager.check_quota(tenant_id):
                    logger.warning(f"⚠️ Tenant {tenant_id} quota exceeded, pausing")
                    break
                
                # Ejecutar ciclo del bot
                bot.run_cycle()
                
        except Exception as e:
            logger.error(f"❌ Error in tenant {tenant_id} bot: {e}")
        finally:
            logger.info(f"🛑 Stopped bot for tenant {tenant_id}")
            if tenant_id in self.bot_instances:
                del self.bot_instances[tenant_id]
    
    def stop_tenant_bot(self, tenant_id: str):
        """Detener bot de tenant"""
        if tenant_id in self.bot_instances:
            bot = self.bot_instances[tenant_id]
            bot.stop()
            del self.bot_instances[tenant_id]
            logger.info(f"✅ Stopped bot for tenant {tenant_id}")
    
    def start_all(self):
        """Iniciar bots para todos los tenants activos"""
        self.running = True
        
        active_tenants = self.tenant_manager.list_tenants(status=TenantStatus.ACTIVE)
        
        logger.info(f"🚀 Starting bots for {len(active_tenants)} active tenants")
        
        for tenant in active_tenants:
            try:
                self.start_tenant_bot(tenant.tenant_id)
            except Exception as e:
                logger.error(f"❌ Failed to start bot for {tenant.name}: {e}")
        
        logger.info(f"✅ All tenant bots started")
    
    def stop_all(self):
        """Detener todos los bots"""
        self.running = False
        
        logger.info(f"🛑 Stopping all tenant bots...")
        
        for tenant_id in list(self.bot_instances.keys()):
            self.stop_tenant_bot(tenant_id)
        
        self.executor.shutdown(wait=True)
        
        logger.info("✅ All tenant bots stopped")
    
    def get_tenant_status(self, tenant_id: str) -> dict:
        """Obtener estado de tenant"""
        tenant = self.tenant_manager.get_tenant(tenant_id)
        if not tenant:
            return {'error': 'Tenant not found'}
        
        bot_running = tenant_id in self.bot_instances
        metrics = self.tenant_manager.get_tenant_metrics(tenant_id)
        
        return {
            'tenant_id': tenant_id,
            'name': tenant.name,
            'tier': tenant.tier.value,
            'status': tenant.status.value,
            'bot_running': bot_running,
            'quota_used': tenant.monthly_trades_used,
            'quota_limit': tenant.monthly_trades_quota,
            'metrics': metrics.__dict__
        }
    
    def print_dashboard(self):
        """Imprimir dashboard de todos los tenants"""
        print("\n" + "="*80)
        print("🏢 MULTI-TENANT DASHBOARD")
        print("="*80)
        
        stats = self.tenant_manager.get_stats()
        print(f"\n📊 Overview:")
        print(f"  Total Tenants: {stats['total_tenants']}")
        print(f"  Running Bots: {len(self.bot_instances)}")
        
        print(f"\n📈 By Tier:")
        for tier, count in stats['by_tier'].items():
            print(f"  {tier}: {count}")
        
        print(f"\n🔄 By Status:")
        for status, count in stats['by_status'].items():
            print(f"  {status}: {count}")
        
        print(f"\n👥 Active Tenants:")
        for tenant in self.tenant_manager.list_tenants(status=TenantStatus.ACTIVE):
            status = self.get_tenant_status(tenant.tenant_id)
            metrics = status['metrics']
            
            print(f"\n  📌 {tenant.name} ({tenant.email})")
            print(f"     Tier: {tenant.tier.value}")
            print(f"     Bot: {'🟢 Running' if status['bot_running'] else '🔴 Stopped'}")
            print(f"     Quota: {status['quota_used']}/{status['quota_limit']}")
            print(f"     Trades: {metrics['total_trades']} (Win Rate: {metrics['win_rate']:.1f}%)")
            print(f"     P&L: ${metrics['total_pnl']:.2f}")
        
        print("\n" + "="*80 + "\n")
```

### 3. API REST para Multi-Tenancy

**Archivo:** `api/tenant_api.py`

```python
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
import jwt
import os

from core.tenant_manager import TenantManager, TenantTier, TenantStatus
from core.multi_tenant_orchestrator import MultiTenantOrchestrator

app = FastAPI(title="BotPolyMarket Multi-Tenant API")
security = HTTPBearer()

# Inicializar
tenant_manager = TenantManager()
orchestrator = MultiTenantOrchestrator()

JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key')

# Models
class TenantCreate(BaseModel):
    name: str
    email: EmailStr
    tier: TenantTier = TenantTier.FREE

class TenantUpdate(BaseModel):
    name: Optional[str] = None
    capital: Optional[float] = None
    tier: Optional[TenantTier] = None
    status: Optional[TenantStatus] = None

# Auth
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verificar JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=['HS256'])
        return payload['tenant_id']
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Endpoints
@app.post("/tenants")
async def create_tenant(tenant: TenantCreate):
    """Crear nuevo tenant"""
    try:
        config = tenant_manager.create_tenant(
            name=tenant.name,
            email=tenant.email,
            tier=tenant.tier
        )
        
        # Generar JWT token
        token = jwt.encode(
            {'tenant_id': config.tenant_id, 'email': config.email},
            JWT_SECRET,
            algorithm='HS256'
        )
        
        return {
            'tenant_id': config.tenant_id,
            'token': token,
            'message': 'Tenant created successfully'
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/tenants/{tenant_id}")
async def get_tenant(tenant_id: str, current_tenant: str = Depends(verify_token)):
    """Obtener información de tenant"""
    # Verificar permiso
    if tenant_id != current_tenant:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    tenant = tenant_manager.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return tenant.__dict__

@app.put("/tenants/{tenant_id}")
async def update_tenant(
    tenant_id: str, 
    updates: TenantUpdate,
    current_tenant: str = Depends(verify_token)
):
    """Actualizar tenant"""
    if tenant_id != current_tenant:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        updated = tenant_manager.update_tenant(
            tenant_id,
            **updates.dict(exclude_none=True)
        )
        return updated.__dict__
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/tenants/{tenant_id}/bot/start")
async def start_bot(tenant_id: str, current_tenant: str = Depends(verify_token)):
    """Iniciar bot de tenant"""
    if tenant_id != current_tenant:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        orchestrator.start_tenant_bot(tenant_id)
        return {'message': 'Bot started successfully'}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/tenants/{tenant_id}/bot/stop")
async def stop_bot(tenant_id: str, current_tenant: str = Depends(verify_token)):
    """Detener bot de tenant"""
    if tenant_id != current_tenant:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    orchestrator.stop_tenant_bot(tenant_id)
    return {'message': 'Bot stopped successfully'}

@app.get("/tenants/{tenant_id}/status")
async def get_status(tenant_id: str, current_tenant: str = Depends(verify_token)):
    """Obtener estado del bot"""
    if tenant_id != current_tenant:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    return orchestrator.get_tenant_status(tenant_id)

@app.get("/tenants/{tenant_id}/metrics")
async def get_metrics(tenant_id: str, current_tenant: str = Depends(verify_token)):
    """Obtener métricas del tenant"""
    if tenant_id != current_tenant:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    metrics = tenant_manager.get_tenant_metrics(tenant_id)
    return metrics.__dict__

# Admin endpoints
@app.get("/admin/tenants")
async def list_tenants(api_key: str = Header(None)):
    """Listar todos los tenants (admin only)"""
    if api_key != os.getenv('ADMIN_API_KEY'):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    tenants = tenant_manager.list_tenants()
    return [t.__dict__ for t in tenants]

@app.get("/admin/stats")
async def get_stats(api_key: str = Header(None)):
    """Estadísticas globales (admin only)"""
    if api_key != os.getenv('ADMIN_API_KEY'):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    return tenant_manager.get_stats()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## Casos de Uso

### Caso 1: SaaS Trading Bot

```python
# Usuarios se registran via web
# Backend crea tenant automáticamente

from api.tenant_api import app
import uvicorn

# Lanzar API
uvicorn.run(app, host="0.0.0.0", port=8000)

# Usuario hace POST /tenants con email/name
# Recibe JWT token
# Configura APIs keys via PUT /tenants/{id}
# Inicia bot con POST /tenants/{id}/bot/start
```

### Caso 2: Hedge Fund con Múltiples Traders

```python
orchestrator = MultiTenantOrchestrator()

# Crear tenant por trader
trader1 = tenant_manager.create_tenant(
    name="John Trader",
    email="john@fund.com",
    tier=TenantTier.PRO
)

trader2 = tenant_manager.create_tenant(
    name="Jane Trader",
    email="jane@fund.com",
    tier=TenantTier.PRO
)

# Configurar cada trader
tenant_manager.update_tenant(trader1.tenant_id, capital=50000.0)
tenant_manager.update_tenant(trader2.tenant_id, capital=75000.0)

# Iniciar todos
orchestrator.start_all()

# Monitorear
orchestrator.print_dashboard()
```

### Caso 3: White Label Solution

```python
# Partner A
partner_a = tenant_manager.create_tenant(
    name="Partner A Corp",
    email="admin@partnera.com",
    tier=TenantTier.ENTERPRISE
)

# Sin límite de trades
tenant_manager.update_tenant(
    partner_a.tenant_id,
    monthly_trades_quota=999999
)

# Custom branding
tenant_manager.update_tenant(
    partner_a.tenant_id,
    custom_domain="bot.partnera.com",
    custom_logo="https://..."
)
```

---

## Seguridad

### 1. Aislamiento de Datos

```python
# Cada tenant tiene su propia base de datos lógica
# Queries siempre filtran por tenant_id

class TenantDatabase:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
    
    def execute(self, query: str, params: tuple):
        # Siempre agregar tenant_id al WHERE
        query += " AND tenant_id = ?"
        params = params + (self.tenant_id,)
        return self._execute(query, params)
```

### 2. Rate Limiting por Tenant

```python
from core.adaptive_rate_limiter import AdaptiveRateLimiter

class TenantRateLimiter:
    def __init__(self):
        self.limiters = {}  # tenant_id -> RateLimiter
    
    def get_limiter(self, tenant_id: str) -> AdaptiveRateLimiter:
        if tenant_id not in self.limiters:
            tenant = tenant_manager.get_tenant(tenant_id)
            
            # Límites según tier
            if tenant.tier == TenantTier.FREE:
                max_requests = 10
            elif tenant.tier == TenantTier.BASIC:
                max_requests = 50
            elif tenant.tier == TenantTier.PRO:
                max_requests = 200
            else:  # ENTERPRISE
                max_requests = 1000
            
            limiter = AdaptiveRateLimiter()
            # Configure limiter...
            self.limiters[tenant_id] = limiter
        
        return self.limiters[tenant_id]
```

### 3. Encryption de Secrets

```python
from cryptography.fernet import Fernet

class SecretManager:
    def __init__(self, encryption_key: bytes):
        self.cipher = Fernet(encryption_key)
    
    def encrypt_api_key(self, api_key: str) -> str:
        return self.cipher.encrypt(api_key.encode()).decode()
    
    def decrypt_api_key(self, encrypted: str) -> str:
        return self.cipher.decrypt(encrypted.encode()).decode()

# Guardar API keys encriptadas
tenant.polymarket_api_key = secret_manager.encrypt_api_key(raw_key)
```

---

## Administración

### CLI Admin Tool

**Archivo:** `scripts/admin_cli.py`

```python
import click
from core.tenant_manager import TenantManager, TenantTier
from core.multi_tenant_orchestrator import MultiTenantOrchestrator

tenant_manager = TenantManager()
orchestrator = MultiTenantOrchestrator()

@click.group()
def cli():
    """BotPolyMarket Multi-Tenant Admin CLI"""
    pass

@cli.command()
@click.option('--name', required=True)
@click.option('--email', required=True)
@click.option('--tier', type=click.Choice(['free', 'basic', 'pro', 'enterprise']), default='free')
def create_tenant(name, email, tier):
    """Crear nuevo tenant"""
    tier_enum = TenantTier(tier)
    tenant = tenant_manager.create_tenant(name, email, tier_enum)
    click.echo(f"✅ Created tenant {tenant.tenant_id}")
    click.echo(f"   Name: {name}")
    click.echo(f"   Email: {email}")
    click.echo(f"   Tier: {tier}")

@cli.command()
def list_tenants():
    """Listar todos los tenants"""
    tenants = tenant_manager.list_tenants()
    
    click.echo(f"\nTotal Tenants: {len(tenants)}\n")
    
    for tenant in tenants:
        click.echo(f"📌 {tenant.name} ({tenant.email})")
        click.echo(f"   ID: {tenant.tenant_id}")
        click.echo(f"   Tier: {tenant.tier.value}")
        click.echo(f"   Status: {tenant.status.value}")
        click.echo(f"   Quota: {tenant.monthly_trades_used}/{tenant.monthly_trades_quota}")
        click.echo()

@cli.command()
@click.argument('tenant_id')
def start_bot(tenant_id):
    """Iniciar bot de tenant"""
    orchestrator.start_tenant_bot(tenant_id)
    click.echo(f"✅ Started bot for tenant {tenant_id}")

@cli.command()
def dashboard():
    """Mostrar dashboard"""
    orchestrator.print_dashboard()

if __name__ == '__main__':
    cli()
```

**Uso:**
```bash
# Crear tenant
python scripts/admin_cli.py create-tenant --name "John" --email "john@example.com" --tier pro

# Listar tenants
python scripts/admin_cli.py list-tenants

# Iniciar bot
python scripts/admin_cli.py start-bot <tenant_id>

# Dashboard
python scripts/admin_cli.py dashboard
```

---

## Billing y Quotas

### Quotas por Tier

| Tier | Trades/Mes | API Calls/Min | Storage | Soporte |
|------|-----------|--------------|---------|--------|
| FREE | 100 | 10 | 100 MB | Email |
| BASIC | 1,000 | 50 | 1 GB | Email + Chat |
| PRO | 10,000 | 200 | 10 GB | 24/7 Phone |
| ENTERPRISE | Unlimited | 1000 | Unlimited | Dedicated |

### Pricing

```python
PRICING = {
    TenantTier.FREE: 0,
    TenantTier.BASIC: 29,  # USD/mes
    TenantTier.PRO: 99,
    TenantTier.ENTERPRISE: 499
}
```

---

## Conclusión

El sistema multi-tenancy permite:

✅ **Monetizar** el bot como SaaS  
✅ **Escalar** a múltiples usuarios  
✅ **Gestión** centralizada y eficiente  
✅ **Aislamiento** total de datos  
✅ **Billing** automatizado por tier  

**Próximos Pasos:**

1. Implementar `TenantManager`
2. Crear `MultiTenantOrchestrator`
3. Setup API REST
4. Configurar billing (Stripe)
5. Deploy en producción

---

**Autor:** juankaspain  
**Versión:** 1.0  
**Fecha:** 2026-01-19
