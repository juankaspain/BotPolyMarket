"""
Database module for BotPolyMarket
Maneja persistencia de trades, métricas y precios históricos
"""

import os
import logging
from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

logger = logging.getLogger(__name__)

Base = declarative_base()


class Trade(Base):
    """Modelo de trades ejecutados"""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    strategy = Column(String(50), nullable=False)
    market_id = Column(String(100), nullable=False)
    market_title = Column(Text)
    side = Column(String(10), nullable=False)  # BUY/SELL
    price = Column(Float, nullable=False)
    size = Column(Float, nullable=False)
    value = Column(Float, nullable=False)
    pnl = Column(Float, default=0.0)
    pnl_pct = Column(Float, default=0.0)
    status = Column(String(20), default='OPEN')  # OPEN/CLOSED
    closed_at = Column(DateTime)
    notes = Column(Text)


class DailyMetric(Base):
    """Métricas diarias del portfolio"""
    __tablename__ = 'daily_metrics'
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, unique=True, nullable=False)
    total_pnl = Column(Float, default=0.0)
    num_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    portfolio_value = Column(Float)
    capital_deployed = Column(Float)


class PriceHistory(Base):
    """Histórico de precios de mercados"""
    __tablename__ = 'price_history'
    
    id = Column(Integer, primary_key=True)
    market_id = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    price = Column(Float, nullable=False)
    volume = Column(Float)
    liquidity = Column(Float)


class RiskEvent(Base):
    """Eventos de riesgo detectados"""
    __tablename__ = 'risk_events'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    event_type = Column(String(50), nullable=False)  # DRAWDOWN/DAILY_LOSS/POSITION_LIMIT
    severity = Column(String(20))  # LOW/MEDIUM/HIGH/CRITICAL
    description = Column(Text)
    action_taken = Column(Text)
    resolved = Column(Boolean, default=False)


class Database:
    """Gestor de base de datos con SQLAlchemy"""
    
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv('DATABASE_URL', 'sqlite:///bot_data.db')
        self.engine = create_engine(self.db_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.create_tables()
        logger.info(f"Database initialized: {self.db_url}")
    
    def create_tables(self):
        """Crea todas las tablas si no existen"""
        Base.metadata.create_all(self.engine)
        logger.info("Database tables created/verified")
    
    @contextmanager
    def get_session(self) -> Session:
        """Context manager para sesiones de base de datos"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    # ==================== TRADES ====================
    
    def save_trade(self, trade_data: Dict) -> Trade:
        """Guarda un nuevo trade"""
        with self.get_session() as session:
            trade = Trade(**trade_data)
            session.add(trade)
            session.flush()
            logger.info(f"Trade saved: {trade.id} - {trade.strategy} {trade.side} {trade.market_title}")
            return trade
    
    def update_trade(self, trade_id: int, updates: Dict):
        """Actualiza un trade existente"""
        with self.get_session() as session:
            trade = session.query(Trade).filter(Trade.id == trade_id).first()
            if trade:
                for key, value in updates.items():
                    setattr(trade, key, value)
                logger.info(f"Trade updated: {trade_id}")
    
    def get_open_trades(self) -> List[Trade]:
        """Obtiene todos los trades abiertos"""
        with self.get_session() as session:
            return session.query(Trade).filter(Trade.status == 'OPEN').all()
    
    def get_trades_by_strategy(self, strategy: str) -> List[Trade]:
        """Obtiene trades por estrategia"""
        with self.get_session() as session:
            return session.query(Trade).filter(Trade.strategy == strategy).all()
    
    def close_trade(self, trade_id: int, close_price: float, pnl: float, pnl_pct: float):
        """Cierra un trade"""
        with self.get_session() as session:
            trade = session.query(Trade).filter(Trade.id == trade_id).first()
            if trade:
                trade.status = 'CLOSED'
                trade.closed_at = datetime.utcnow()
                trade.pnl = pnl
                trade.pnl_pct = pnl_pct
                logger.info(f"Trade closed: {trade_id} | PnL: ${pnl:.2f} ({pnl_pct:.2f}%)")
    
    # ==================== MÉTRICAS ====================
    
    def save_daily_metrics(self, metrics: Dict):
        """Guarda métricas diarias"""
        with self.get_session() as session:
            metric = DailyMetric(**metrics)
            session.add(metric)
            logger.info(f"Daily metrics saved for {metrics.get('date')}")
    
    def get_metrics_range(self, start_date: datetime, end_date: datetime) -> List[DailyMetric]:
        """Obtiene métricas en un rango de fechas"""
        with self.get_session() as session:
            return session.query(DailyMetric)\
                .filter(DailyMetric.date >= start_date)\
                .filter(DailyMetric.date <= end_date)\
                .order_by(DailyMetric.date)\
                .all()
    
    # ==================== PRECIOS ====================
    
    def save_price(self, market_id: str, price: float, volume: float = None, liquidity: float = None):
        """Guarda precio histórico"""
        with self.get_session() as session:
            price_entry = PriceHistory(
                market_id=market_id,
                price=price,
                volume=volume,
                liquidity=liquidity
            )
            session.add(price_entry)
    
    def get_price_history(self, market_id: str, limit: int = 100) -> List[PriceHistory]:
        """Obtiene historial de precios"""
        with self.get_session() as session:
            return session.query(PriceHistory)\
                .filter(PriceHistory.market_id == market_id)\
                .order_by(PriceHistory.timestamp.desc())\
                .limit(limit)\
                .all()
    
    # ==================== RIESGO ====================
    
    def log_risk_event(self, event_type: str, severity: str, description: str, action: str = None):
        """Registra evento de riesgo"""
        with self.get_session() as session:
            event = RiskEvent(
                event_type=event_type,
                severity=severity,
                description=description,
                action_taken=action
            )
            session.add(event)
            logger.warning(f"Risk event logged: {event_type} - {severity}")
    
    def get_unresolved_risk_events(self) -> List[RiskEvent]:
        """Obtiene eventos de riesgo no resueltos"""
        with self.get_session() as session:
            return session.query(RiskEvent).filter(RiskEvent.resolved == False).all()
