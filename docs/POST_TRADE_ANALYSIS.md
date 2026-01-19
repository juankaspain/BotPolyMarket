# Post-Trade Analysis System
**Sistema de Análisis Detallado Post-Trade para BotPolyMarket**

## 📋 Tabla de Contenidos

- [Introducción](#introducción)
- [Arquitectura](#arquitectura)
- [Reportes Automáticos](#reportes-automáticos)
- [Visualizaciones](#visualizaciones)
- [Performance Attribution](#performance-attribution)
- [Integración](#integración)

---

## Introducción

### ¿Qué es Post-Trade Analysis?

Sistema que **analiza cada trade completado** para identificar:
- ✅ Qué funcionó
- ❌ Qué falló
- 📊 Patrones recurrentes
- 💡 Oportunidades de mejora

### Beneficios

✅ **Mejora continua** de estrategias  
✅ **Identificación** de patrones ganadores  
✅ **Detección** de errores sistemáticos  
✅ **Reportes** para auditoría/compliance  
✅ **Insights** accionables  

---

## Arquitectura

### Trade Record

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum

class TradeStatus(Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TradeType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"

@dataclass
class TradeRecord:
    """Registro completo de un trade"""
    # Identificación
    trade_id: str
    timestamp: datetime
    market_id: str
    strategy_name: str
    
    # Ejecución
    side: str  # buy/sell
    trade_type: TradeType
    status: TradeStatus
    
    # Precios
    entry_price: float
    exit_price: Optional[float] = None
    slippage: float = 0.0
    
    # Tamaños
    planned_size: float = 0.0
    executed_size: float = 0.0
    
    # Costos
    fees: float = 0.0
    gas_cost: float = 0.0
    
    # Timing
    entry_time: datetime = None
    exit_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    # Performance
    gross_pnl: float = 0.0
    net_pnl: float = 0.0
    roi: float = 0.0
    
    # Contexto
    market_conditions: Dict = field(default_factory=dict)
    signal_confidence: float = 0.0
    signal_reason: str = ""
    
    # Análisis
    notes: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    quality_score: Optional[float] = None
    
    def calculate_metrics(self):
        """Calcular métricas derivadas"""
        if self.exit_price and self.entry_price:
            # P&L
            if self.side == "buy":
                self.gross_pnl = (self.exit_price - self.entry_price) * self.executed_size
            else:
                self.gross_pnl = (self.entry_price - self.exit_price) * self.executed_size
            
            self.net_pnl = self.gross_pnl - self.fees - self.gas_cost
            
            # ROI
            investment = self.entry_price * self.executed_size
            self.roi = (self.net_pnl / investment * 100) if investment > 0 else 0.0
            
            # Duration
            if self.exit_time and self.entry_time:
                self.duration_seconds = (self.exit_time - self.entry_time).total_seconds()
            
            # Slippage
            expected_exit = self.entry_price * (1 + 0.01)  # Ejemplo: 1% target
            self.slippage = abs(self.exit_price - expected_exit) / expected_exit * 100
```

### Post-Trade Analyzer

```python
import logging
import sqlite3
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np

logger = logging.getLogger(__name__)

class PostTradeAnalyzer:
    """Analizador de trades completados"""
    
    def __init__(self, db_path: str = "data/trades.db"):
        self.db_path = db_path
        self._init_database()
        
        logger.info("✅ PostTradeAnalyzer initialized")
    
    def _init_database(self):
        """Crear base de datos de trades"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY,
                timestamp TIMESTAMP,
                market_id TEXT,
                strategy_name TEXT,
                side TEXT,
                trade_type TEXT,
                status TEXT,
                entry_price REAL,
                exit_price REAL,
                slippage REAL,
                planned_size REAL,
                executed_size REAL,
                fees REAL,
                gas_cost REAL,
                entry_time TIMESTAMP,
                exit_time TIMESTAMP,
                duration_seconds REAL,
                gross_pnl REAL,
                net_pnl REAL,
                roi REAL,
                signal_confidence REAL,
                signal_reason TEXT,
                quality_score REAL,
                market_conditions TEXT,
                notes TEXT,
                tags TEXT
            )
        ''')
        
        # Índices
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON trades(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_strategy ON trades(strategy_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON trades(status)')
        
        conn.commit()
        conn.close()
    
    def record_trade(self, trade: TradeRecord):
        """Registrar trade"""
        # Calcular métricas
        trade.calculate_metrics()
        
        # Guardar en DB
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO trades VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        ''', (
            trade.trade_id,
            trade.timestamp.isoformat(),
            trade.market_id,
            trade.strategy_name,
            trade.side,
            trade.trade_type.value,
            trade.status.value,
            trade.entry_price,
            trade.exit_price,
            trade.slippage,
            trade.planned_size,
            trade.executed_size,
            trade.fees,
            trade.gas_cost,
            trade.entry_time.isoformat() if trade.entry_time else None,
            trade.exit_time.isoformat() if trade.exit_time else None,
            trade.duration_seconds,
            trade.gross_pnl,
            trade.net_pnl,
            trade.roi,
            trade.signal_confidence,
            trade.signal_reason,
            trade.quality_score,
            str(trade.market_conditions),
            '|'.join(trade.notes),
            ','.join(trade.tags)
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Recorded trade {trade.trade_id} ({trade.strategy_name})")
    
    def get_trades(self, 
                   strategy: str = None,
                   start_date: datetime = None,
                   end_date: datetime = None) -> pd.DataFrame:
        """Obtener trades como DataFrame"""
        query = "SELECT * FROM trades WHERE 1=1"
        params = []
        
        if strategy:
            query += " AND strategy_name = ?"
            params.append(strategy)
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())
        
        query += " ORDER BY timestamp DESC"
        
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
    
    def analyze_trade(self, trade_id: str) -> Dict:
        """Análisis detallado de un trade específico"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM trades WHERE trade_id = ?', (trade_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {'error': 'Trade not found'}
        
        # Análisis
        analysis = {
            'trade_id': row[0],
            'summary': self._generate_trade_summary(row),
            'strengths': self._identify_strengths(row),
            'weaknesses': self._identify_weaknesses(row),
            'lessons': self._extract_lessons(row),
            'recommendations': self._generate_recommendations(row)
        }
        
        return analysis
    
    def _generate_trade_summary(self, row: tuple) -> str:
        """Generar resumen del trade"""
        strategy, side, net_pnl, roi = row[3], row[4], row[18], row[19]
        
        result = "WIN" if net_pnl > 0 else "LOSS"
        
        return f"{strategy} {side.upper()} trade - {result}: ${net_pnl:.2f} ({roi:.2f}% ROI)"
    
    def _identify_strengths(self, row: tuple) -> List[str]:
        """Identificar fortalezas del trade"""
        strengths = []
        
        # ROI alto
        if row[19] > 5:  # roi
            strengths.append(f"Excellent ROI of {row[19]:.2f}%")
        
        # Baja comisión
        if row[12] / row[11] < 0.001:  # fees / executed_size
            strengths.append("Low transaction fees")
        
        # Alta confianza en señal
        if row[20] > 0.8:  # signal_confidence
            strengths.append(f"High signal confidence ({row[20]:.1%})")
        
        # Ejecución rápida
        if row[16] and row[16] < 60:  # duration_seconds
            strengths.append(f"Fast execution ({row[16]:.0f}s)")
        
        return strengths
    
    def _identify_weaknesses(self, row: tuple) -> List[str]:
        """Identificar debilidades del trade"""
        weaknesses = []
        
        # Slippage alto
        if row[9] > 1.0:  # slippage
            weaknesses.append(f"High slippage ({row[9]:.2f}%)")
        
        # Ejecución parcial
        if row[11] < row[10] * 0.9:  # executed < planned * 0.9
            fill_rate = row[11] / row[10] * 100
            weaknesses.append(f"Partial fill ({fill_rate:.1f}%)")
        
        # Gas cost alto
        if row[13] > row[18] * 0.1:  # gas_cost > net_pnl * 10%
            weaknesses.append(f"High gas cost (${row[13]:.2f})")
        
        # Baja confianza pero ejecutado
        if row[20] < 0.5:  # signal_confidence
            weaknesses.append(f"Low signal confidence ({row[20]:.1%})")
        
        return weaknesses
    
    def _extract_lessons(self, row: tuple) -> List[str]:
        """Extraer lecciones del trade"""
        lessons = []
        
        net_pnl = row[18]
        
        if net_pnl < 0:
            # Trade perdedor
            if row[9] > 2.0:  # slippage
                lessons.append("Avoid trading during high volatility periods")
            
            if row[20] < 0.6:  # signal_confidence
                lessons.append("Only trade signals with confidence >60%")
            
            if row[16] and row[16] > 300:  # duration > 5min
                lessons.append("Consider tighter stop-losses for longer trades")
        else:
            # Trade ganador
            strategy = row[3]
            lessons.append(f"Strategy '{strategy}' works well in these conditions")
            
            if row[20] > 0.8:
                lessons.append("High-confidence signals tend to be profitable")
        
        return lessons
    
    def _generate_recommendations(self, row: tuple) -> List[str]:
        """Generar recomendaciones"""
        recommendations = []
        
        # Slippage
        if row[9] > 1.5:
            recommendations.append("Use limit orders instead of market orders")
        
        # Gas optimization
        if row[13] > 5:  # gas_cost > $5
            recommendations.append("Batch multiple trades to reduce gas costs")
        
        # Position sizing
        if row[11] < 100:  # executed_size < $100
            recommendations.append("Increase position size to improve cost efficiency")
        
        # Timing
        if row[16] and row[16] > 600:  # duration > 10min
            recommendations.append("Set tighter time limits for trade execution")
        
        return recommendations
    
    def generate_report(self, 
                       strategy: str = None,
                       period_days: int = 30) -> Dict:
        """Generar reporte completo"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        df = self.get_trades(strategy=strategy, start_date=start_date, end_date=end_date)
        
        if df.empty:
            return {'error': 'No trades found'}
        
        # Métricas básicas
        total_trades = len(df)
        winning_trades = len(df[df['net_pnl'] > 0])
        losing_trades = len(df[df['net_pnl'] < 0])
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        
        # P&L
        total_pnl = df['net_pnl'].sum()
        avg_win = df[df['net_pnl'] > 0]['net_pnl'].mean() if winning_trades > 0 else 0
        avg_loss = df[df['net_pnl'] < 0]['net_pnl'].mean() if losing_trades > 0 else 0
        
        # Risk metrics
        profit_factor = abs(avg_win * winning_trades / (avg_loss * losing_trades)) if losing_trades > 0 else float('inf')
        sharpe_ratio = df['roi'].mean() / df['roi'].std() * np.sqrt(252) if len(df) > 1 else 0
        
        # Best/Worst
        best_trade = df.loc[df['net_pnl'].idxmax()] if not df.empty else None
        worst_trade = df.loc[df['net_pnl'].idxmin()] if not df.empty else None
        
        report = {
            'period': f"{start_date.date()} to {end_date.date()}",
            'strategy': strategy or 'All strategies',
            'summary': {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': round(win_rate, 2),
                'total_pnl': round(total_pnl, 2),
                'avg_pnl_per_trade': round(total_pnl / total_trades, 2) if total_trades > 0 else 0
            },
            'performance': {
                'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
                'profit_factor': round(profit_factor, 2),
                'sharpe_ratio': round(sharpe_ratio, 2),
                'max_win': round(df['net_pnl'].max(), 2),
                'max_loss': round(df['net_pnl'].min(), 2)
            },
            'costs': {
                'total_fees': round(df['fees'].sum(), 2),
                'total_gas': round(df['gas_cost'].sum(), 2),
                'avg_slippage': round(df['slippage'].mean(), 3)
            },
            'best_trade': {
                'trade_id': best_trade['trade_id'],
                'strategy': best_trade['strategy_name'],
                'pnl': round(best_trade['net_pnl'], 2)
            } if best_trade is not None else None,
            'worst_trade': {
                'trade_id': worst_trade['trade_id'],
                'strategy': worst_trade['strategy_name'],
                'pnl': round(worst_trade['net_pnl'], 2)
            } if worst_trade is not None else None,
            'by_strategy': self._analyze_by_strategy(df),
            'recommendations': self._generate_portfolio_recommendations(df)
        }
        
        return report
    
    def _analyze_by_strategy(self, df: pd.DataFrame) -> Dict:
        """Análisis agrupado por estrategia"""
        by_strategy = {}
        
        for strategy in df['strategy_name'].unique():
            strategy_df = df[df['strategy_name'] == strategy]
            
            by_strategy[strategy] = {
                'trades': len(strategy_df),
                'win_rate': len(strategy_df[strategy_df['net_pnl'] > 0]) / len(strategy_df) * 100,
                'total_pnl': round(strategy_df['net_pnl'].sum(), 2),
                'avg_roi': round(strategy_df['roi'].mean(), 2)
            }
        
        return by_strategy
    
    def _generate_portfolio_recommendations(self, df: pd.DataFrame) -> List[str]:
        """Recomendaciones a nivel portfolio"""
        recommendations = []
        
        # Win rate bajo
        win_rate = len(df[df['net_pnl'] > 0]) / len(df) * 100
        if win_rate < 50:
            recommendations.append(f"Win rate is low ({win_rate:.1f}%). Review entry criteria.")
        
        # Profit factor bajo
        wins = df[df['net_pnl'] > 0]['net_pnl'].sum()
        losses = abs(df[df['net_pnl'] < 0]['net_pnl'].sum())
        profit_factor = wins / losses if losses > 0 else float('inf')
        
        if profit_factor < 1.5:
            recommendations.append(f"Profit factor is low ({profit_factor:.2f}). Improve win size or reduce losses.")
        
        # Costos altos
        total_pnl = df['net_pnl'].sum()
        total_fees = df['fees'].sum() + df['gas_cost'].sum()
        
        if total_fees > abs(total_pnl) * 0.3:
            recommendations.append("Transaction costs are eating profits. Reduce trade frequency.")
        
        # Estrategia dominante
        by_strategy = df.groupby('strategy_name')['net_pnl'].sum()
        best_strategy = by_strategy.idxmax()
        
        recommendations.append(f"Strategy '{best_strategy}' is performing best. Consider allocating more capital.")
        
        return recommendations
    
    def export_report(self, report: Dict, output_path: str = "reports/trade_analysis.json"):
        """Exportar reporte a archivo"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"✅ Report exported to {output_path}")
```

---

## Reportes Automáticos

### Daily Report Email

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class ReportMailer:
    """Enviar reportes por email"""
    
    def __init__(self, smtp_config: Dict):
        self.smtp_host = smtp_config['host']
        self.smtp_port = smtp_config['port']
        self.username = smtp_config['username']
        self.password = smtp_config['password']
    
    def send_daily_report(self, analyzer: PostTradeAnalyzer, to_email: str):
        """Enviar reporte diario"""
        report = analyzer.generate_report(period_days=1)
        
        # Crear HTML
        html = self._format_html_report(report)
        
        # Enviar email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Daily Trading Report - {datetime.now().date()}"
        msg['From'] = self.username
        msg['To'] = to_email
        
        msg.attach(MIMEText(html, 'html'))
        
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
        
        logger.info(f"✅ Daily report sent to {to_email}")
    
    def _format_html_report(self, report: Dict) -> str:
        """Formatear reporte como HTML"""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .metric {{ margin: 10px 0; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
            </style>
        </head>
        <body>
            <h1>📊 Daily Trading Report</h1>
            <p><strong>Period:</strong> {report['period']}</p>
            
            <h2>Summary</h2>
            <div class="metric">Total Trades: {report['summary']['total_trades']}</div>
            <div class="metric">Win Rate: {report['summary']['win_rate']}%</div>
            <div class="metric">Total P&L: <span class="{'positive' if report['summary']['total_pnl'] > 0 else 'negative'}">${report['summary']['total_pnl']}</span></div>
            
            <h2>Performance</h2>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Avg Win</td><td>${report['performance']['avg_win']}</td></tr>
                <tr><td>Avg Loss</td><td>${report['performance']['avg_loss']}</td></tr>
                <tr><td>Profit Factor</td><td>{report['performance']['profit_factor']}</td></tr>
                <tr><td>Sharpe Ratio</td><td>{report['performance']['sharpe_ratio']}</td></tr>
            </table>
            
            <h2>Recommendations</h2>
            <ul>
        """
        
        for rec in report['recommendations']:
            html += f"<li>{rec}</li>"
        
        html += """
            </ul>
        </body>
        </html>
        """
        
        return html
```

---

## Conclusión

El Post-Trade Analysis System proporciona:

✅ **Análisis automático** de cada trade  
✅ **Reportes detallados** con insights  
✅ **Identificación** de patrones  
✅ **Recomendaciones** accionables  
✅ **Mejora continua** del bot  

---

**Autor:** juankaspain  
**Versión:** 1.0  
**Fecha:** 2026-01-19
