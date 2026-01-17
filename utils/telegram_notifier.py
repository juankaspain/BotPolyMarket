#!/usr/bin/env python3
"""
Telegram Notifier v2.0
Envía alertas de gaps y métricas de ROI a Telegram
"""
import logging
from typing import Dict, Optional
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """
    Notificador de Telegram para alertas del bot
    
    Tipos de alertas:
    - Gap detectado (con ML probability)
    - Trade ejecutado
    - Trade cerrado (con ROI)
    - Métricas diarias
    - Errores críticos
    """
    
    def __init__(self, config: dict):
        self.bot_token = config.get('telegram_bot_token', '')
        self.chat_id = config.get('telegram_chat_id', '')
        self.enabled = bool(self.bot_token and self.chat_id)
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        if not self.enabled:
            logger.warning("⚠️ Telegram notifier deshabilitado (falta token o chat_id)")
        else:
            logger.info("✅ Telegram notifier habilitado")
    
    def send_message(self, message: str, parse_mode: str = 'HTML'):
        """
        Envía un mensaje a Telegram
        
        Args:
            message: Texto del mensaje
            parse_mode: 'HTML' o 'Markdown'
        """
        if not self.enabled:
            return
        
        try:
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            response = requests.post(self.api_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.debug("✅ Mensaje enviado a Telegram")
            else:
                logger.warning(f"⚠️ Error enviando mensaje: {response.status_code}")
        
        except Exception as e:
            logger.error(f"❌ Error con Telegram API: {e}")
    
    def notify_gap_detected(self, gap_data: Dict):
        """
        Notifica un gap detectado
        
        Args:
            gap_data: {
                'market_slug': str,
                'gap_size': float,
                'ml_probability': float,
                'sentiment': float,
                'recommendation': str
            }
        """
        market = gap_data.get('market_slug', 'Unknown')
        gap_size = gap_data.get('gap_size', 0)
        ml_prob = gap_data.get('ml_probability', 0)
        sentiment = gap_data.get('sentiment', 0)
        recommendation = gap_data.get('recommendation', 'SKIP')
        
        # Emoji según recommendation
        emoji = '🟢' if recommendation == 'EXECUTE' else '🟡'
        
        message = f"""
{emoji} <b>GAP DETECTADO</b>

📊 Market: <code>{market}</code>
💰 Gap Size: <b>{gap_size:.1f}¢</b>
🤖 ML Probability: <b>{ml_prob:.1%}</b>
😊 Sentiment: <b>{sentiment:+.2f}</b>

✅ Recommendation: <b>{recommendation}</b>
🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        self.send_message(message)
    
    def notify_trade_executed(self, trade_data: Dict):
        """
        Notifica un trade ejecutado
        
        Args:
            trade_data: {
                'id': str,
                'market_slug': str,
                'entry_price': float,
                'size': float,
                'ml_probability': float
            }
        """
        trade_id = trade_data.get('id', 'Unknown')
        market = trade_data.get('market_slug', 'Unknown')
        entry = trade_data.get('entry_price', 0)
        size = trade_data.get('size', 0)
        ml_prob = trade_data.get('ml_probability', 0)
        
        message = f"""
🚀 <b>TRADE EJECUTADO</b>

🆔 ID: <code>{trade_id}</code>
📊 Market: <code>{market}</code>
💵 Entry: <b>${entry:.4f}</b>
💰 Size: <b>${size:.2f} USDC</b>
🤖 ML Confidence: <b>{ml_prob:.1%}</b>

⏳ Esperando cierre...
🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        self.send_message(message)
    
    def notify_trade_closed(self, trade_data: Dict):
        """
        Notifica un trade cerrado
        
        Args:
            trade_data: {
                'id': str,
                'market_slug': str,
                'entry_price': float,
                'exit_price': float,
                'roi': float,
                'size': float,
                'pnl': float
            }
        """
        trade_id = trade_data.get('id', 'Unknown')
        market = trade_data.get('market_slug', 'Unknown')
        entry = trade_data.get('entry_price', 0)
        exit_price = trade_data.get('exit_price', 0)
        roi = trade_data.get('roi', 0)
        size = trade_data.get('size', 0)
        pnl = trade_data.get('pnl', 0)
        
        # Emoji según resultado
        emoji = '✅' if roi > 0 else '❌'
        
        message = f"""
{emoji} <b>TRADE CERRADO</b>

🆔 ID: <code>{trade_id}</code>
📊 Market: <code>{market}</code>

💵 Entry: ${entry:.4f}
💵 Exit: ${exit_price:.4f}
📈 ROI: <b>{roi:+.2%}</b>
💰 P&L: <b>${pnl:+.2f} USDC</b>

📦 Size: ${size:.2f}
🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        self.send_message(message)
    
    def notify_daily_summary(self, metrics: Dict):
        """
        Envía resumen diario de métricas
        
        Args:
            metrics: PortfolioMetrics dict
        """
        total_capital = metrics.get('total_capital', 0)
        total_roi = metrics.get('total_roi', 0)
        win_rate = metrics.get('win_rate', 0)
        total_trades = metrics.get('total_trades', 0)
        winning = metrics.get('winning_trades', 0)
        losing = metrics.get('losing_trades', 0)
        sharpe = metrics.get('sharpe_ratio', 0)
        max_dd = metrics.get('max_drawdown', 0)
        
        message = f"""
📊 <b>RESUMEN DIARIO</b>
{'='*30}

💰 Capital Total: <b>${total_capital:,.2f}</b>
📈 ROI Total: <b>{total_roi:+.2%}</b>

🎯 Win Rate: <b>{win_rate:.1%}</b>
📊 Trades: {total_trades} ({winning}W / {losing}L)

⚠️ Sharpe: <b>{sharpe:.2f}</b>
📉 Max DD: <b>{max_dd:.2%}</b>

🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*30}
        """
        
        self.send_message(message)
    
    def notify_error(self, error_msg: str, context: Optional[str] = None):
        """
        Notifica un error crítico
        
        Args:
            error_msg: Mensaje de error
            context: Contexto adicional (opcional)
        """
        context_str = f"\n\n📝 Context: <code>{context}</code>" if context else ""
        
        message = f"""
🚨 <b>ERROR CRÍTICO</b>

❌ {error_msg}{context_str}

🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        self.send_message(message)
    
    def notify_milestone(self, milestone: str, value: float):
        """
        Notifica un milestone alcanzado
        
        Args:
            milestone: Tipo de milestone ('roi', 'capital', 'win_rate', etc.)
            value: Valor alcanzado
        """
        emoji_map = {
            'roi': '🎯',
            'capital': '💰',
            'win_rate': '🏆',
            'trades': '📊'
        }
        
        emoji = emoji_map.get(milestone, '🎉')
        
        message = f"""
{emoji} <b>MILESTONE ALCANZADO!</b>

🎊 {milestone.upper()}: <b>{value}</b>

🚀 Keep going!
🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        self.send_message(message)
