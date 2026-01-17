"""dashboard.py
Dashboard de monitoreo en tiempo real para el Bot de Copy Trading

Proporciona visualización web de:
- Estado del bot y estrategia activa
- Rendimiento y métricas en tiempo real
- Historial de trades
- Oportunidades detectadas
- Alertas y notificaciones

Autor: juankaspain
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from flask import Flask, render_template, jsonify, request
from threading import Thread
import time

logger = logging.getLogger(__name__)


class Dashboard:
    """
    Dashboard web para monitoreo del bot de trading
    
    Proporciona interfaz web usando Flask para visualizar:
    - Estado del bot en tiempo real
    - Métricas de rendimiento
    - Historial de operaciones
    - Oportunidades detectadas
    - Sistema de alertas
    """
    
    def __init__(self, bot_manager, port: int = 5000, host: str = '127.0.0.1'):
        """
        Inicializa el dashboard
        
        Args:
            bot_manager: Instancia del BotManager
            port: Puerto para el servidor web (default: 5000)
            host: Host para el servidor (default: '127.0.0.1')
        """
        self.bot_manager = bot_manager
        self.port = port
        self.host = host
        self.app = Flask(__name__)
        self.is_running = False
        
        # Configurar rutas
        self._setup_routes()
        
        logger.info(f"Dashboard inicializado en {host}:{port}")
    
    def _setup_routes(self):
        """Configura las rutas del dashboard"""
        
        @self.app.route('/')
        def index():
            """Página principal del dashboard"""
            return self._render_dashboard()
        
        @self.app.route('/api/status')
        def api_status():
            """API: Estado actual del bot"""
            return jsonify(self._get_bot_status())
        
        @self.app.route('/api/metrics')
        def api_metrics():
            """API: Métricas de rendimiento"""
            return jsonify(self._get_metrics())
        
        @self.app.route('/api/trades')
        def api_trades():
            """API: Historial de trades"""
            limit = request.args.get('limit', 50, type=int)
            return jsonify(self._get_trades(limit))
        
        @self.app.route('/api/opportunities')
        def api_opportunities():
            """API: Oportunidades detectadas"""
            return jsonify(self._get_opportunities())
        
        @self.app.route('/api/alerts')
        def api_alerts():
            """API: Alertas activas"""
            return jsonify(self._get_alerts())
    
    def _get_bot_status(self) -> Dict:
        """Obtiene el estado actual del bot"""
        try:
            return {
                'status': self.bot_manager.status.value,
                'strategy': self.bot_manager.current_strategy.value if self.bot_manager.current_strategy else None,
                'uptime': self._calculate_uptime(),
                'total_trades': self.bot_manager.total_trades,
                'successful_trades': self.bot_manager.successful_trades,
                'failed_trades': self.bot_manager.failed_trades,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error obteniendo estado del bot: {e}")
            return {'error': str(e)}
    
    def _get_metrics(self) -> Dict:
        """Obtiene métricas de rendimiento"""
        try:
            portfolio = self.bot_manager.portfolio
            
            return {
                'balance': portfolio.get_balance(),
                'pnl': portfolio.get_total_pnl(),
                'pnl_percentage': portfolio.get_pnl_percentage(),
                'win_rate': self._calculate_win_rate(),
                'avg_profit': self._calculate_avg_profit(),
                'best_trade': self._get_best_trade(),
                'worst_trade': self._get_worst_trade(),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error obteniendo métricas: {e}")
            return {'error': str(e)}
    
    def _get_trades(self, limit: int = 50) -> Dict:
        """Obtiene historial de trades"""
        try:
            trades = self.bot_manager.db.get_recent_trades(limit)
            
            return {
                'trades': trades,
                'count': len(trades),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error obteniendo trades: {e}")
            return {'error': str(e)}
    
    def _get_opportunities(self) -> Dict:
        """Obtiene oportunidades detectadas"""
        try:
            if not hasattr(self.bot_manager, 'opportunity_analyzer'):
                return {'opportunities': [], 'count': 0}
            
            opportunities = self.bot_manager.opportunity_analyzer.get_recent_opportunities()
            
            return {
                'opportunities': opportunities,
                'count': len(opportunities),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error obteniendo oportunidades: {e}")
            return {'error': str(e)}
    
    def _get_alerts(self) -> Dict:
        """Obtiene alertas activas"""
        try:
            circuit_breakers = self.bot_manager.circuit_breaker_manager.get_status_all()
            alerts = []
            
            for name, status in circuit_breakers.items():
                if status['state'] != 'closed':
                    alerts.append({
                        'type': 'circuit_breaker',
                        'service': name,
                        'state': status['state'],
                        'failures': status['failures'],
                        'severity': 'high' if status['state'] == 'open' else 'medium'
                    })
            
            return {
                'alerts': alerts,
                'count': len(alerts),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error obteniendo alertas: {e}")
            return {'error': str(e)}
    
    def _calculate_uptime(self) -> str:
        """Calcula el tiempo de actividad del bot"""
        if not self.bot_manager.start_time:
            return "0:00:00"
        
        uptime = datetime.now() - self.bot_manager.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return f"{hours}:{minutes:02}:{seconds:02}"
    
    def _calculate_win_rate(self) -> float:
        """Calcula el porcentaje de trades exitosos"""
        total = self.bot_manager.total_trades
        if total == 0:
            return 0.0
        
        return (self.bot_manager.successful_trades / total) * 100
    
    def _calculate_avg_profit(self) -> float:
        """Calcula el profit promedio por trade"""
        try:
            trades = self.bot_manager.db.get_recent_trades(100)
            if not trades:
                return 0.0
            
            total_profit = sum(trade.get('pnl', 0) for trade in trades)
            return total_profit / len(trades)
        except:
            return 0.0
    
    def _get_best_trade(self) -> Dict:
        """Obtiene el mejor trade"""
        try:
            return self.bot_manager.db.get_best_trade()
        except:
            return {}
    
    def _get_worst_trade(self) -> Dict:
        """Obtiene el peor trade"""
        try:
            return self.bot_manager.db.get_worst_trade()
        except:
            return {}
    
    def _render_dashboard(self) -> str:
        """Renderiza el HTML del dashboard"""
        return '''<!DOCTYPE html>
<html>
<head>
    <title>BotPolyMarket - Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f0f23; color: #e0e0e0; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        h1 { color: #00ff88; margin-bottom: 30px; text-align: center; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .card { background: #1a1a2e; border-radius: 8px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .card h2 { color: #00ff88; margin-bottom: 15px; font-size: 1.2em; }
        .metric { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #2a2a3e; }
        .metric:last-child { border-bottom: none; }
        .metric-label { color: #888; }
        .metric-value { color: #fff; font-weight: bold; }
        .status { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 0.85em; font-weight: bold; }
        .status.running { background: #00ff88; color: #0f0f23; }
        .status.stopped { background: #ff4444; color: #fff; }
        .status.paused { background: #ffaa00; color: #0f0f23; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #2a2a3e; }
        th { color: #00ff88; font-weight: 600; }
        .positive { color: #00ff88; }
        .negative { color: #ff4444; }
        .alert { background: #ff4444; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔥 BotPolyMarket - Dashboard de Trading</h1>
        
        <div id="alerts"></div>
        
        <div class="grid">
            <div class="card">
                <h2>📊 Estado del Bot</h2>
                <div id="bot-status"></div>
            </div>
            <div class="card">
                <h2>💰 Métricas de Rendimiento</h2>
                <div id="metrics"></div>
            </div>
            <div class="card">
                <h2>🎯 Oportunidades</h2>
                <div id="opportunities"></div>
            </div>
        </div>
        
        <div class="card">
            <h2>💼 Historial de Trades Recientes</h2>
            <div id="trades"></div>
        </div>
    </div>
    
    <script>
        async function fetchData() {
            try {
                const [status, metrics, trades, opportunities, alerts] = await Promise.all([
                    fetch('/api/status').then(r => r.json()),
                    fetch('/api/metrics').then(r => r.json()),
                    fetch('/api/trades?limit=20').then(r => r.json()),
                    fetch('/api/opportunities').then(r => r.json()),
                    fetch('/api/alerts').then(r => r.json())
                ]);
                
                updateStatus(status);
                updateMetrics(metrics);
                updateTrades(trades);
                updateOpportunities(opportunities);
                updateAlerts(alerts);
            } catch (e) {
                console.error('Error fetching data:', e);
            }
        }
        
        function updateStatus(data) {
            document.getElementById('bot-status').innerHTML = `
                <div class="metric"><span class="metric-label">Estado:</span><span class="status ${data.status}">${data.status.toUpperCase()}</span></div>
                <div class="metric"><span class="metric-label">Estrategia:</span><span class="metric-value">${data.strategy || 'No seleccionada'}</span></div>
                <div class="metric"><span class="metric-label">Uptime:</span><span class="metric-value">${data.uptime}</span></div>
                <div class="metric"><span class="metric-label">Total Trades:</span><span class="metric-value">${data.total_trades}</span></div>
                <div class="metric"><span class="metric-label">Exitosos:</span><span class="metric-value positive">${data.successful_trades}</span></div>
                <div class="metric"><span class="metric-label">Fallidos:</span><span class="metric-value negative">${data.failed_trades}</span></div>
            `;
        }
        
        function updateMetrics(data) {
            document.getElementById('metrics').innerHTML = `
                <div class="metric"><span class="metric-label">Balance:</span><span class="metric-value">$${data.balance?.toFixed(2) || '0.00'}</span></div>
                <div class="metric"><span class="metric-label">PnL:</span><span class="metric-value ${data.pnl >= 0 ? 'positive' : 'negative'}">$${data.pnl?.toFixed(2) || '0.00'}</span></div>
                <div class="metric"><span class="metric-label">PnL %:</span><span class="metric-value ${data.pnl_percentage >= 0 ? 'positive' : 'negative'}">${data.pnl_percentage?.toFixed(2) || '0.00'}%</span></div>
                <div class="metric"><span class="metric-label">Win Rate:</span><span class="metric-value">${data.win_rate?.toFixed(2) || '0.00'}%</span></div>
                <div class="metric"><span class="metric-label">Profit Promedio:</span><span class="metric-value">$${data.avg_profit?.toFixed(2) || '0.00'}</span></div>
            `;
        }
        
        function updateTrades(data) {
            if (!data.trades || data.trades.length === 0) {
                document.getElementById('trades').innerHTML = '<p style="color: #888; text-align: center; padding: 20px;">No hay trades recientes</p>';
                return;
            }
            
            const html = `
                <table>
                    <tr><th>Fecha</th><th>Tipo</th><th>Market</th><th>Cantidad</th><th>Precio</th><th>PnL</th></tr>
                    ${data.trades.map(t => `
                        <tr>
                            <td>${new Date(t.timestamp).toLocaleString()}</td>
                            <td>${t.type}</td>
                            <td>${t.market || 'N/A'}</td>
                            <td>${t.amount}</td>
                            <td>$${t.price?.toFixed(2)}</td>
                            <td class="${t.pnl >= 0 ? 'positive' : 'negative'}">$${t.pnl?.toFixed(2) || '0.00'}</td>
                        </tr>
                    `).join('')}
                </table>
            `;
            document.getElementById('trades').innerHTML = html;
        }
        
        function updateOpportunities(data) {
            const count = data.count || 0;
            document.getElementById('opportunities').innerHTML = `
                <div class="metric"><span class="metric-label">Detectadas:</span><span class="metric-value">${count}</span></div>
                <div class="metric"><span class="metric-label">Última actualización:</span><span class="metric-value">${new Date().toLocaleTimeString()}</span></div>
            `;
        }
        
        function updateAlerts(data) {
            if (!data.alerts || data.alerts.length === 0) {
                document.getElementById('alerts').innerHTML = '';
                return;
            }
            
            const html = data.alerts.map(alert => `
                <div class="alert">
                    <strong>⚠️ Alerta: ${alert.service}</strong> - Estado: ${alert.state} (${alert.failures} fallos)
                </div>
            `).join('');
            document.getElementById('alerts').innerHTML = html;
        }
        
        // Actualizar cada 5 segundos
        fetchData();
        setInterval(fetchData, 5000);
    </script>
</body>
</html>
        '''
    
    def start(self, debug: bool = False):
        """
        Inicia el servidor del dashboard
        
        Args:
            debug: Modo debug de Flask (default: False)
        """
        if self.is_running:
            logger.warning("Dashboard ya está en ejecución")
            return
        
        self.is_running = True
        logger.info(f"Iniciando dashboard en http://{self.host}:{self.port}")
        
        # Ejecutar en thread separado para no bloquear
        thread = Thread(target=self._run_server, args=(debug,))
        thread.daemon = True
        thread.start()
    
    def _run_server(self, debug: bool):
        """Ejecuta el servidor Flask"""
        try:
            self.app.run(host=self.host, port=self.port, debug=debug, use_reloader=False)
        except Exception as e:
            logger.error(f"Error ejecutando servidor: {e}")
            self.is_running = False
    
    def stop(self):
        """Detiene el servidor del dashboard"""
        self.is_running = False
        logger.info("Dashboard detenido")
