#!/usr/bin/env python3
"""
Telegram Notifier v2.0
Envía alertas y reportes de ROI via Telegram
"""
import logging
from typing import Dict, Optional
from datetime import datetime
import asyncio

try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """
    Notificador de Telegram para alertas y reportes
    
    Features:
    - Alertas de gaps detectados
    - Reportes de ROI diarios/semanales
    - Alertas de trades ejecutados
    - Notificaciones de errores críticos
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.bot_token = config.get('telegram_bot_token')
        self.chat_id = config.get('telegram_chat_id')
        self.enabled = config.get('telegram_enabled', False)
        self.bot = None
        
        if not TELEGRAM_AVAILABLE:
            logger.warning("⚠️ python-telegram-bot no disponible. Instalar: pip install python-telegram-bot")
            self.enabled = False
            return
        
        if self.enabled and self.bot_token and self.chat_id:
            try:
                self.bot = Bot(token=self.bot_token)
                logger.info("✅ Telegram bot inicializado")
            except Exception as e:
                logger.error(f"❌ Error inicializando Telegram bot: {e}")
                self.enabled = False
        else:
            logger.info("ℹ️ Telegram notifier deshabilitado")
    
    async def send_message(self, message: str, parse_mode: str = 'HTML') -> bool:
        """
        Envía un mensaje a Telegram
        
        Args:
            message: Texto del mensaje (soporta HTML o Markdown)
            parse_mode: 'HTML' o 'Markdown'
        
        Returns:
            True si éxito, False si error
        """
        if not self.enabled or not self.bot:
            return False
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
            return True
        except TelegramError as e:
            logger.error(f"❌ Error enviando mensaje Telegram: {e}")
            return False
    
    def send_message_sync(self, message: str, parse_mode: str = 'HTML') -> bool:
        """
        Versión síncrona de send_message
        """
        if not self.enabled:
            return False
        
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.send_message(message, parse_mode))
        except RuntimeError:
            # Si no hay event loop, crear uno nuevo
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.send_message(message, parse_mode))
            loop.close()
            return result
    
    def send_gap_alert(self, gap_data: Dict) -> bool:
        """
        Envía alerta de gap detectado
        
        Args:
            gap_data: {
                'market': str,
                'gap_size': float,
                'prediction': dict,  # De MLGapPredictor
                'timestamp': datetime
            }
        """
        prediction = gap_data.get('prediction', {})
        prob = prediction.get('probability', 0)
        confidence = prediction.get('confidence', 'N/A')
        sentiment = prediction.get('sentiment', 0)
        
        # Emoji según confianza
        emoji = '🟢' if confidence == 'HIGH' else '🟡' if confidence == 'MEDIUM' else '🔴'
        
        message = f"""
{emoji} <b>GAP DETECTADO</b> {emoji}

<b>Mercado:</b> {gap_data.get('market', 'N/A')}
<b>Gap Size:</b> {gap_data.get('gap_size', 0):.2f}¢
<b>Probabilidad:</b> {prob:.1%}
<b>Confianza:</b> {confidence}
<b>Sentiment:</b> {sentiment:+.2f}
<b>Recomendación:</b> {prediction.get('recommendation', 'N/A')}

⏰ {gap_data.get('timestamp', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        return self.send_message_sync(message)
    
    def send_trade_execution(self, trade_data: Dict) -> bool:
        """
        Envía notificación de trade ejecutado
        
        Args:
            trade_data: {
                'market': str,
                'side': str,  # 'BUY' o 'SELL'
                'amount': float,
                'price': float,
                'expected_roi': float
            }
        """
        message = f"""
💰 <b>TRADE EJECUTADO</b>

<b>Mercado:</b> {trade_data.get('market', 'N/A')}
<b>Acción:</b> {trade_data.get('side', 'N/A')}
<b>Cantidad:</b> ${trade_data.get('amount', 0):.2f}
<b>Precio:</b> {trade_data.get('price', 0):.4f}
<b>ROI Esperado:</b> {trade_data.get('expected_roi', 0):.1%}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        return self.send_message_sync(message)
    
    def send_roi_report(self, report_data: Dict) -> bool:
        """
        Envía reporte diario/semanal de ROI
        
        Args:
            report_data: {
                'period': str,  # 'daily', 'weekly'
                'total_trades': int,
                'winning_trades': int,
                'win_rate': float,
                'total_roi': float,
                'total_profit': float,
                'capital': float,
                'sharpe_ratio': float
            }
        """
        period = report_data.get('period', 'daily').upper()
        win_rate = report_data.get('win_rate', 0)
        roi = report_data.get('total_roi', 0)
        
        # Emoji según performance
        emoji = '🚀' if roi > 0.1 else '📈' if roi > 0 else '📉'
        
        message = f"""
{emoji} <b>REPORTE {period}</b> {emoji}

<b>📊 Trades</b>
• Total: {report_data.get('total_trades', 0)}
• Ganadores: {report_data.get('winning_trades', 0)}
• Win Rate: {win_rate:.1%}

<b>💰 Performance</b>
• ROI: {roi:+.2%}
• Profit: ${report_data.get('total_profit', 0):+,.2f}
• Capital: ${report_data.get('capital', 0):,.2f}
• Sharpe: {report_data.get('sharpe_ratio', 0):.2f}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        return self.send_message_sync(message)
    
    def send_error_alert(self, error_msg: str, context: str = '') -> bool:
        """
        Envía alerta de error crítico
        
        Args:
            error_msg: Mensaje de error
            context: Contexto adicional
        """
        message = f"""
🚨 <b>ERROR CRÍTICO</b> 🚨

<b>Error:</b> {error_msg}

{f'<b>Contexto:</b> {context}' if context else ''}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        return self.send_message_sync(message)
