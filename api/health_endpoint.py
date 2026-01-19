#!/usr/bin/env python3
"""Health Check Endpoint for BotPolyMarket

Provides comprehensive system health monitoring:
- API status
- Database connectivity
- WebSocket connections
- External API availability
- System resources (CPU, Memory, Disk)
- Trading bot status
- Last activity timestamps

Usage:
    GET /health - Basic health check
    GET /health/detailed - Detailed health report
    GET /health/metrics - Prometheus-compatible metrics

Author: juankaspain
Version: 7.0
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import psutil
import os
import sys
import time
import asyncio
import aiohttp

app = FastAPI(title="BotPolyMarket Health API", version="7.0")

# Health check configuration
CHECK_TIMEOUT = 5  # seconds
LAST_ACTIVITY_FILE = "data/last_activity.json"

class HealthStatus(BaseModel):
    """Health status model"""
    status: str  # healthy, degraded, unhealthy
    timestamp: str
    uptime: float
    version: str

class ComponentHealth(BaseModel):
    """Individual component health"""
    name: str
    status: str
    latency_ms: Optional[float] = None
    message: Optional[str] = None
    last_check: str

class DetailedHealth(BaseModel):
    """Detailed health report"""
    overall_status: str
    timestamp: str
    uptime_seconds: float
    components: List[ComponentHealth]
    system: Dict[str, any]
    trading: Dict[str, any]

# Startup time for uptime calculation
START_TIME = time.time()

def get_uptime() -> float:
    """Get system uptime in seconds"""
    return time.time() - START_TIME

def check_database() -> ComponentHealth:
    """Check database connectivity"""
    start = time.time()
    
    try:
        from core.database import Database
        
        db = Database({})
        # Try a simple query
        db.get_trades(limit=1)
        
        latency = (time.time() - start) * 1000
        
        return ComponentHealth(
            name="database",
            status="healthy",
            latency_ms=round(latency, 2),
            message="PostgreSQL/SQLite operational",
            last_check=datetime.now().isoformat()
        )
    except Exception as e:
        return ComponentHealth(
            name="database",
            status="unhealthy",
            message=f"Database error: {str(e)}",
            last_check=datetime.now().isoformat()
        )

async def check_polymarket_api() -> ComponentHealth:
    """Check Polymarket API availability"""
    start = time.time()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://clob.polymarket.com/markets",
                timeout=aiohttp.ClientTimeout(total=CHECK_TIMEOUT)
            ) as response:
                latency = (time.time() - start) * 1000
                
                if response.status == 200:
                    return ComponentHealth(
                        name="polymarket_api",
                        status="healthy",
                        latency_ms=round(latency, 2),
                        message="Polymarket API responsive",
                        last_check=datetime.now().isoformat()
                    )
                else:
                    return ComponentHealth(
                        name="polymarket_api",
                        status="degraded",
                        latency_ms=round(latency, 2),
                        message=f"API returned status {response.status}",
                        last_check=datetime.now().isoformat()
                    )
    except Exception as e:
        return ComponentHealth(
            name="polymarket_api",
            status="unhealthy",
            message=f"API unreachable: {str(e)}",
            last_check=datetime.now().isoformat()
        )

async def check_external_apis() -> List[ComponentHealth]:
    """Check external API availability (Binance, Kalshi)"""
    results = []
    
    # Check Binance
    try:
        async with aiohttp.ClientSession() as session:
            start = time.time()
            async with session.get(
                "https://api.binance.com/api/v3/ping",
                timeout=aiohttp.ClientTimeout(total=CHECK_TIMEOUT)
            ) as response:
                latency = (time.time() - start) * 1000
                
                results.append(ComponentHealth(
                    name="binance_api",
                    status="healthy" if response.status == 200 else "degraded",
                    latency_ms=round(latency, 2),
                    message="Binance API operational",
                    last_check=datetime.now().isoformat()
                ))
    except Exception as e:
        results.append(ComponentHealth(
            name="binance_api",
            status="unhealthy",
            message=str(e),
            last_check=datetime.now().isoformat()
        ))
    
    # Check Kalshi
    try:
        async with aiohttp.ClientSession() as session:
            start = time.time()
            async with session.get(
                "https://api.kalshi.com/v1/exchange/status",
                timeout=aiohttp.ClientTimeout(total=CHECK_TIMEOUT)
            ) as response:
                latency = (time.time() - start) * 1000
                
                results.append(ComponentHealth(
                    name="kalshi_api",
                    status="healthy" if response.status == 200 else "degraded",
                    latency_ms=round(latency, 2),
                    message="Kalshi API operational",
                    last_check=datetime.now().isoformat()
                ))
    except Exception as e:
        results.append(ComponentHealth(
            name="kalshi_api",
            status="unhealthy",
            message=str(e),
            last_check=datetime.now().isoformat()
        ))
    
    return results

def check_websocket() -> ComponentHealth:
    """Check WebSocket connection status"""
    try:
        from core.websocket_handler import WebSocketHandler
        
        ws = WebSocketHandler({})
        is_connected = ws.is_connected() if hasattr(ws, 'is_connected') else True
        
        return ComponentHealth(
            name="websocket",
            status="healthy" if is_connected else "degraded",
            message="WebSocket connection active" if is_connected else "WebSocket disconnected",
            last_check=datetime.now().isoformat()
        )
    except Exception as e:
        return ComponentHealth(
            name="websocket",
            status="unhealthy",
            message=f"WebSocket error: {str(e)}",
            last_check=datetime.now().isoformat()
        )

def get_system_metrics() -> Dict[str, any]:
    """Get system resource metrics"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_usage_percent": round(cpu_percent, 2),
            "memory_usage_percent": round(memory.percent, 2),
            "memory_available_mb": round(memory.available / (1024 ** 2), 2),
            "disk_usage_percent": round(disk.percent, 2),
            "disk_free_gb": round(disk.free / (1024 ** 3), 2),
            "python_version": sys.version.split()[0],
            "process_id": os.getpid()
        }
    except Exception as e:
        return {"error": str(e)}

def get_trading_status() -> Dict[str, any]:
    """Get trading bot status"""
    try:
        import json
        
        # Read last activity
        if os.path.exists(LAST_ACTIVITY_FILE):
            with open(LAST_ACTIVITY_FILE, 'r') as f:
                activity = json.load(f)
            
            last_trade_time = activity.get('last_trade')
            last_scan_time = activity.get('last_scan')
            
            return {
                "bot_running": True,
                "last_trade": last_trade_time,
                "last_scan": last_scan_time,
                "active_positions": activity.get('active_positions', 0),
                "total_trades_today": activity.get('trades_today', 0),
                "pnl_today": activity.get('pnl_today', 0.0)
            }
        else:
            return {
                "bot_running": False,
                "message": "No recent activity detected"
            }
    except Exception as e:
        return {"error": str(e)}

def calculate_overall_status(components: List[ComponentHealth]) -> str:
    """Calculate overall health status from components"""
    statuses = [c.status for c in components]
    
    if all(s == "healthy" for s in statuses):
        return "healthy"
    elif any(s == "unhealthy" for s in statuses):
        return "unhealthy"
    else:
        return "degraded"

@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Basic health check endpoint"""
    return HealthStatus(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        uptime=round(get_uptime(), 2),
        version="7.0"
    )

@app.get("/health/detailed", response_model=DetailedHealth)
async def detailed_health_check():
    """Detailed health check with all components"""
    components = []
    
    # Check database
    components.append(check_database())
    
    # Check Polymarket API
    polymarket_health = await check_polymarket_api()
    components.append(polymarket_health)
    
    # Check external APIs
    external_health = await check_external_apis()
    components.extend(external_health)
    
    # Check WebSocket
    components.append(check_websocket())
    
    # Calculate overall status
    overall = calculate_overall_status(components)
    
    return DetailedHealth(
        overall_status=overall,
        timestamp=datetime.now().isoformat(),
        uptime_seconds=round(get_uptime(), 2),
        components=components,
        system=get_system_metrics(),
        trading=get_trading_status()
    )

@app.get("/health/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """Prometheus-compatible metrics endpoint"""
    metrics = []
    
    # System metrics
    system = get_system_metrics()
    metrics.append(f"# HELP system_cpu_usage CPU usage percentage")
    metrics.append(f"# TYPE system_cpu_usage gauge")
    metrics.append(f"system_cpu_usage {system.get('cpu_usage_percent', 0)}")
    
    metrics.append(f"# HELP system_memory_usage Memory usage percentage")
    metrics.append(f"# TYPE system_memory_usage gauge")
    metrics.append(f"system_memory_usage {system.get('memory_usage_percent', 0)}")
    
    # Trading metrics
    trading = get_trading_status()
    metrics.append(f"# HELP bot_active_positions Number of active positions")
    metrics.append(f"# TYPE bot_active_positions gauge")
    metrics.append(f"bot_active_positions {trading.get('active_positions', 0)}")
    
    metrics.append(f"# HELP bot_pnl_today Today's P&L")
    metrics.append(f"# TYPE bot_pnl_today gauge")
    metrics.append(f"bot_pnl_today {trading.get('pnl_today', 0.0)}")
    
    # Uptime
    metrics.append(f"# HELP bot_uptime_seconds Bot uptime in seconds")
    metrics.append(f"# TYPE bot_uptime_seconds counter")
    metrics.append(f"bot_uptime_seconds {get_uptime()}")
    
    return "\n".join(metrics)

@app.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe"""
    # Check critical components
    db_health = check_database()
    api_health = await check_polymarket_api()
    
    if db_health.status == "healthy" and api_health.status in ["healthy", "degraded"]:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"ready": True}
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )

@app.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    # Simple check that service is running
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"alive": True}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
