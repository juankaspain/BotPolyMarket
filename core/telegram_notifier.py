"""Telegram Notifier - v2.0 ML Gap Predictor

Alertas en tiempo real de gaps detectados, trades ejecutados y ROI tracking.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TradeAlert:
    """Alerta de trade"""
    timestamp: datetime
    market_name: str
    gap_size: float
    predicted_probability: float
    actual_probability: float
    position_size: float
    expected_roi: float
    status: str  # 'pending', 'executed', 'filled', 'closed'


@dataclass
class ROIStats:
    """Estadísticas de ROI"""
    initial_capital: float
    current_capital: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_profit: float
    total_loss: float
    win_rate: float
    roi_percentage: float
    sharpe_ratio: float
    max_drawdown: float
    avg_gap_accuracy: float


class TelegramNotifier:
    """Gestor de notificaciones Telegram con ROI tracking"""
    
    def __init__(self, bot_token: str, chat_ids: List[str]):
        """Inicializar notificador
        
        Args:
            bot_token: Token del bot de Telegram
            chat_ids: Lista de IDs de chat para enviar notificaciones
        """
        self.bot_token = bot_token
        self.chat_ids = chat_ids
        self.bot: Optional[Bot] = None
        self.application: Optional[Application] = None
        
        # ROI tracking
        self.initial_capital = float(os.getenv('INITIAL_CAPITAL', '1500'))
        self.trades_history: List[TradeAlert] = []
        self.roi_stats: Optional[ROIStats] = None
        
        # Rate limiting
        self.last_alert_time: Dict[str, datetime] = {}
        self.min_alert_interval = timedelta(minutes=5)  # Evitar spam
        
    async def initialize(self):
        """Inicializar bot de Telegram"""
        try:
            self.bot = Bot(token=self.bot_token)
            self.application = Application.builder().token(self.bot_token).build()
            
            # Registrar comandos
            self.application.add_handler(CommandHandler("status", self._status_command))
            self.application.add_handler(CommandHandler("roi", self._roi_command))
            self.application.add_handler(CommandHandler("stats", self._stats_command))
            self.application.add_handler(CommandHandler("trades", self._trades_command))
            
            logger.info("Telegram notifier initialized successfully")
            
            # Enviar mensaje de inicio
            await self.send_startup_message()
            
        except Exception as e:
            logger.error(f"Error initializing Telegram bot: {e}")
            raise
    
    async def send_startup_message(self):
        """Enviar mensaje de inicio del bot"""
        message = (
            "🤖 *BotPolyMarket v2.0 - ML Gap Predictor*\n\n"
            "✅ Bot iniciado correctamente\n"
            f"💰 Capital inicial: ${self.initial_capital:.2f}\n\n"
            "📊 Comandos disponibles:\n"
            "/status - Estado actual del bot\n"
            "/roi - Resumen de ROI y rendimiento\n"
            "/stats - Estadísticas detalladas\n"
            "/trades - Últimos trades ejecutados\n\n"
            "🎯 Target: 78% win rate | ROI: +130%"
        )
        await self._broadcast_message(message, parse_mode='Markdown')
    
    async def send_gap_alert(self, 
                            market_name: str,
                            gap_size: float,
                            predicted_prob: float,
                            actual_prob: float,
                            confidence: float,
                            ml_features: Dict):
        """Enviar alerta de gap detectado
        
        Args:
            market_name: Nombre del mercado
            gap_size: Tamaño del gap en centavos
            predicted_prob: Probabilidad predicha por ML
            actual_prob: Probabilidad actual del mercado
            confidence: Nivel de confianza de la predicción
            ml_features: Features usados en la predicción
        """
        # Rate limiting
        alert_key = f"gap_{market_name}"
        if not self._can_send_alert(alert_key):
            return
        
        # Emoji según tamaño del gap
        emoji = "🔥" if gap_size >= 10 else "⚡" if gap_size >= 5 else "📊"
        
        message = (
            f"{emoji} *GAP DETECTADO*\n\n"
            f"📈 Market: {market_name[:50]}\n"
            f"💵 Gap: {gap_size:.2f}¢ ({gap_size/100:.2%})\n\n"
            f"🤖 ML Prediction:\n"
            f"  • Predicted: {predicted_prob:.1%}\n"
            f"  • Actual: {actual_prob:.1%}\n"
            f"  • Confidence: {confidence:.1%}\n\n"
            f"📊 ML Features:\n"
            f"  • Sentiment: {ml_features.get('sentiment_score', 0):.2f}\n"
            f"  • Volume Trend: {ml_features.get('volume_trend', 0):.2f}\n"
            f"  • Price Momentum: {ml_features.get('price_momentum', 0):.2f}\n\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S')}"
        )
        
        await self._broadcast_message(message, parse_mode='Markdown')
        self.last_alert_time[alert_key] = datetime.now()
    
    async def send_trade_executed(self,
                                 market_name: str,
                                 side: str,
                                 size: float,
                                 price: float,
                                 expected_roi: float):
        """Enviar alerta de trade ejecutado
        
        Args:
            market_name: Nombre del mercado
            side: 'BUY' o 'SELL'
            size: Tamaño de la posición en USDC
            price: Precio de entrada
            expected_roi: ROI esperado del trade
        """
        emoji = "🟢" if side == "BUY" else "🔴"
        
        message = (
            f"{emoji} *TRADE EJECUTADO*\n\n"
            f"📊 Market: {market_name[:50]}\n"
            f"📍 Side: {side}\n"
            f"💰 Size: ${size:.2f} USDC\n"
            f"💵 Price: {price:.4f}\n"
            f"🎯 Expected ROI: {expected_roi:.2%}\n\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S')}"
        )
        
        await self._broadcast_message(message, parse_mode='Markdown')
        
        # Registrar trade
        trade = TradeAlert(
            timestamp=datetime.now(),
            market_name=market_name,
            gap_size=0,  # Se actualizará después
            predicted_probability=price,
            actual_probability=price,
            position_size=size,
            expected_roi=expected_roi,
            status='executed'
        )
        self.trades_history.append(trade)
    
    async def send_trade_closed(self,
                               market_name: str,
                               entry_price: float,
                               exit_price: float,
                               pnl: float,
                               roi: float,
                               duration: timedelta):
        """Enviar alerta de trade cerrado con P&L
        
        Args:
            market_name: Nombre del mercado
            entry_price: Precio de entrada
            exit_price: Precio de salida
            pnl: Profit/Loss en USDC
            roi: ROI del trade
            duration: Duración del trade
        """
        emoji = "✅" if pnl > 0 else "❌"
        
        message = (
            f"{emoji} *TRADE CERRADO*\n\n"
            f"📊 Market: {market_name[:50]}\n"
            f"📍 Entry: {entry_price:.4f}\n"
            f"📍 Exit: {exit_price:.4f}\n"
            f"💰 P&L: ${pnl:+.2f} ({roi:+.2%})\n"
            f"⏱ Duration: {self._format_duration(duration)}\n\n"
        )
        
        # Añadir stats actualizados
        await self._update_roi_stats()
        if self.roi_stats:
            message += (
                f"📈 *Portfolio Stats:*\n"
                f"  • Total Trades: {self.roi_stats.total_trades}\n"
                f"  • Win Rate: {self.roi_stats.win_rate:.1%}\n"
                f"  • Total ROI: {self.roi_stats.roi_percentage:+.2%}\n"
                f"  • Capital: ${self.roi_stats.current_capital:.2f}\n"
            )
        
        await self._broadcast_message(message, parse_mode='Markdown')
    
    async def send_daily_summary(self):
        """Enviar resumen diario de actividad"""
        await self._update_roi_stats()
        
        if not self.roi_stats:
            return
        
        # Calcular trades del día
        today = datetime.now().date()
        today_trades = [t for t in self.trades_history 
                       if t.timestamp.date() == today]
        
        message = (
            "📊 *RESUMEN DIARIO*\n\n"
            f"📅 {datetime.now().strftime('%d/%m/%Y')}\n\n"
            f"💰 *Capital:*\n"
            f"  • Inicial: ${self.initial_capital:.2f}\n"
            f"  • Actual: ${self.roi_stats.current_capital:.2f}\n"
            f"  • ROI: {self.roi_stats.roi_percentage:+.2%}\n\n"
            f"📈 *Performance:*\n"
            f"  • Trades hoy: {len(today_trades)}\n"
            f"  • Trades total: {self.roi_stats.total_trades}\n"
            f"  • Win Rate: {self.roi_stats.win_rate:.1%}\n"
            f"  • Sharpe: {self.roi_stats.sharpe_ratio:.2f}\n\n"
            f"💵 *P&L:*\n"
            f"  • Profit: ${self.roi_stats.total_profit:.2f}\n"
            f"  • Loss: ${abs(self.roi_stats.total_loss):.2f}\n"
            f"  • Net: ${self.roi_stats.total_profit + self.roi_stats.total_loss:+.2f}\n\n"
            f"🎯 Target v2.0: 78% WR | +130% ROI\n"
            f"📊 Gap Accuracy: {self.roi_stats.avg_gap_accuracy:.1%}"
        )
        
        await self._broadcast_message(message, parse_mode='Markdown')
    
    async def send_error_alert(self, error_type: str, error_message: str):
        """Enviar alerta de error crítico
        
        Args:
            error_type: Tipo de error
            error_message: Mensaje de error
        """
        message = (
            "🚨 *ERROR CRÍTICO*\n\n"
            f"❌ Type: {error_type}\n"
            f"📝 Message: {error_message[:200]}\n\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S')}"
        )
        
        await self._broadcast_message(message, parse_mode='Markdown')
    
    async def _update_roi_stats(self):
        """Actualizar estadísticas de ROI"""
        if not self.trades_history:
            return
        
        # Calcular métricas
        total_trades = len(self.trades_history)
        winning_trades = sum(1 for t in self.trades_history if t.expected_roi > 0)
        losing_trades = total_trades - winning_trades
        
        total_profit = sum(t.expected_roi * t.position_size 
                          for t in self.trades_history if t.expected_roi > 0)
        total_loss = sum(t.expected_roi * t.position_size 
                        for t in self.trades_history if t.expected_roi < 0)
        
        current_capital = self.initial_capital + total_profit + total_loss
        roi_percentage = (current_capital - self.initial_capital) / self.initial_capital
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Calcular Sharpe (simplificado)
        returns = [t.expected_roi for t in self.trades_history]
        avg_return = sum(returns) / len(returns) if returns else 0
        std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5 if returns else 1
        sharpe_ratio = (avg_return / std_return) * (252 ** 0.5) if std_return > 0 else 0
        
        # Calcular max drawdown (simplificado)
        capital_curve = [self.initial_capital]
        for trade in self.trades_history:
            capital_curve.append(capital_curve[-1] + trade.expected_roi * trade.position_size)
        
        peak = capital_curve[0]
        max_dd = 0
        for capital in capital_curve:
            if capital > peak:
                peak = capital
            dd = (peak - capital) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        
        # Gap accuracy (simplificado)
        gap_accuracy = win_rate  # Aproximación simple
        
        self.roi_stats = ROIStats(
            initial_capital=self.initial_capital,
            current_capital=current_capital,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            total_profit=total_profit,
            total_loss=total_loss,
            win_rate=win_rate,
            roi_percentage=roi_percentage,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_dd,
            avg_gap_accuracy=gap_accuracy
        )
    
    def _can_send_alert(self, alert_key: str) -> bool:
        """Verificar si se puede enviar alerta (rate limiting)"""
        if alert_key not in self.last_alert_time:
            return True
        
        elapsed = datetime.now() - self.last_alert_time[alert_key]
        return elapsed >= self.min_alert_interval
    
    async def _broadcast_message(self, message: str, parse_mode: str = None):
        """Enviar mensaje a todos los chats configurados"""
        if not self.bot:
            logger.error("Bot not initialized")
            return
        
        for chat_id in self.chat_ids:
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode=parse_mode
                )
            except Exception as e:
                logger.error(f"Error sending message to {chat_id}: {e}")
    
    @staticmethod
    def _format_duration(duration: timedelta) -> str:
        """Formatear duración en formato legible"""
        hours, remainder = divmod(duration.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if duration.days > 0:
            return f"{duration.days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m {seconds}s"
    
    # Comandos de Telegram
    async def _status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /status"""
        message = (
            "🤖 *Bot Status*\n\n"
            "✅ Running\n"
            f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
            "Use /roi para ver rendimiento"
        )
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def _roi_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /roi"""
        await self._update_roi_stats()
        
        if not self.roi_stats:
            await update.message.reply_text("No hay datos de trading aún")
            return
        
        message = (
            "💰 *ROI TRACKER*\n\n"
            f"Capital Inicial: ${self.roi_stats.initial_capital:.2f}\n"
            f"Capital Actual: ${self.roi_stats.current_capital:.2f}\n"
            f"ROI: {self.roi_stats.roi_percentage:+.2%}\n\n"
            f"Trades: {self.roi_stats.total_trades}\n"
            f"Win Rate: {self.roi_stats.win_rate:.1%}\n"
            f"Sharpe: {self.roi_stats.sharpe_ratio:.2f}\n\n"
            f"🎯 Target: 78% WR | +130% ROI"
        )
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def _stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /stats"""
        await self._update_roi_stats()
        
        if not self.roi_stats:
            await update.message.reply_text("No hay datos de trading aún")
            return
        
        message = (
            "📊 *ESTADÍSTICAS DETALLADAS*\n\n"
            f"💰 *Capital:*\n"
            f"  Inicial: ${self.roi_stats.initial_capital:.2f}\n"
            f"  Actual: ${self.roi_stats.current_capital:.2f}\n"
            f"  ROI: {self.roi_stats.roi_percentage:+.2%}\n\n"
            f"📈 *Trades:*\n"
            f"  Total: {self.roi_stats.total_trades}\n"
            f"  Ganadores: {self.roi_stats.winning_trades}\n"
            f"  Perdedores: {self.roi_stats.losing_trades}\n"
            f"  Win Rate: {self.roi_stats.win_rate:.1%}\n\n"
            f"💵 *P&L:*\n"
            f"  Profit: ${self.roi_stats.total_profit:.2f}\n"
            f"  Loss: ${abs(self.roi_stats.total_loss):.2f}\n"
            f"  Net: ${self.roi_stats.total_profit + self.roi_stats.total_loss:+.2f}\n\n"
            f"📊 *Risk Metrics:*\n"
            f"  Sharpe: {self.roi_stats.sharpe_ratio:.2f}\n"
            f"  Max DD: {self.roi_stats.max_drawdown:.2%}\n"
            f"  Gap Acc: {self.roi_stats.avg_gap_accuracy:.1%}"
        )
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def _trades_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /trades"""
        if not self.trades_history:
            await update.message.reply_text("No hay trades registrados aún")
            return
        
        # Mostrar últimos 5 trades
        recent_trades = self.trades_history[-5:]
        
        message = "📊 *ÚLTIMOS TRADES*\n\n"
        for i, trade in enumerate(reversed(recent_trades), 1):
            roi_emoji = "✅" if trade.expected_roi > 0 else "❌"
            message += (
                f"{i}. {roi_emoji} {trade.market_name[:30]}\n"
                f"   ${trade.position_size:.0f} | ROI: {trade.expected_roi:+.2%}\n"
                f"   {trade.timestamp.strftime('%d/%m %H:%M')}\n\n"
            )
        
        await update.message.reply_text(message, parse_mode='Markdown')
