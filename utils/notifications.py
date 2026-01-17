"""notifications.py
Sistema de Notificaciones para el Bot de Polymarket

Soporta múltiples canales:
- Telegram
- Email (SMTP)
- Discord (opcional)
- Webhooks (opcional)

Autor: juankaspain
"""

import logging
import os
from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Tipos de notificaciones"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    TRADE = "trade"
    OPPORTUNITY = "opportunity"


class NotificationManager:
    """
    Gestor de notificaciones multi-canal
    
    Envía notificaciones a través de diferentes canales configurados.
    """
    
    def __init__(self, config: Dict = None):
        """
        Inicializa el gestor de notificaciones
        
        Args:
            config: Configuración de canales de notificación
        """
        self.config = config or self._load_config_from_env()
        
        # Canales habilitados
        self.telegram_enabled = self.config.get('telegram_enabled', False)
        self.email_enabled = self.config.get('email_enabled', False)
        self.discord_enabled = self.config.get('discord_enabled', False)
        
        # Configuración Telegram
        self.telegram_token = self.config.get('telegram_token')
        self.telegram_chat_id = self.config.get('telegram_chat_id')
        
        # Configuración Email
        self.smtp_server = self.config.get('smtp_server')
        self.smtp_port = self.config.get('smtp_port', 587)
        self.smtp_username = self.config.get('smtp_username')
        self.smtp_password = self.config.get('smtp_password')
        self.email_from = self.config.get('email_from')
        self.email_to = self.config.get('email_to')
        
        # Configuración Discord
        self.discord_webhook = self.config.get('discord_webhook')
        
        logger.info(f"NotificationManager inicializado - Telegram: {self.telegram_enabled}, Email: {self.email_enabled}")
    
    def _load_config_from_env(self) -> Dict:
        """Carga configuración desde variables de entorno"""
        return {
            # Telegram
            'telegram_enabled': os.getenv('TELEGRAM_ENABLED', 'false').lower() == 'true',
            'telegram_token': os.getenv('TELEGRAM_BOT_TOKEN'),
            'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID'),
            
            # Email
            'email_enabled': os.getenv('EMAIL_ENABLED', 'false').lower() == 'true',
            'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', 587)),
            'smtp_username': os.getenv('SMTP_USERNAME'),
            'smtp_password': os.getenv('SMTP_PASSWORD'),
            'email_from': os.getenv('EMAIL_FROM'),
            'email_to': os.getenv('EMAIL_TO'),
            
            # Discord
            'discord_enabled': os.getenv('DISCORD_ENABLED', 'false').lower() == 'true',
            'discord_webhook': os.getenv('DISCORD_WEBHOOK'),
        }
    
    def send(self, message: str, notification_type: NotificationType = NotificationType.INFO, **kwargs):
        """
        Envía notificación a todos los canales habilitados
        
        Args:
            message: Mensaje a enviar
            notification_type: Tipo de notificación
            **kwargs: Datos adicionales
        """
        success_count = 0
        
        # Enviar a Telegram
        if self.telegram_enabled:
            if self._send_telegram(message, notification_type):
                success_count += 1
        
        # Enviar a Email
        if self.email_enabled:
            if self._send_email(message, notification_type, **kwargs):
                success_count += 1
        
        # Enviar a Discord
        if self.discord_enabled:
            if self._send_discord(message, notification_type):
                success_count += 1
        
        if success_count > 0:
            logger.debug(f"Notificación enviada a {success_count} canal(es)")
        else:
            logger.warning("No se pudo enviar notificación a ningún canal")
    
    def _send_telegram(self, message: str, notification_type: NotificationType) -> bool:
        """
        Envía notificación por Telegram
        
        Returns:
            True si se envió correctamente
        """
        if not requests:
            logger.error("requests no está instalado. No se puede enviar Telegram.")
            return False
        
        if not self.telegram_token or not self.telegram_chat_id:
            logger.error("Telegram no configurado correctamente")
            return False
        
        try:
            # Formatear mensaje con emojis
            emoji = self._get_emoji(notification_type)
            formatted_message = f"{emoji} {message}"
            
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                "chat_id": self.telegram_chat_id,
                "text": formatted_message,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                logger.debug("Notificación Telegram enviada")
                return True
            else:
                logger.error(f"Error enviando Telegram: {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Excepción al enviar Telegram: {e}")
            return False

          def _send_email(self, message: str, notification_type: NotificationType, **kwargs) -> bool:
        """
        Envía notificación por Email
        
        Returns:
            True si se envió correctamente
        """
        if not smtplib:
            logger.error("smtplib no está disponible. No se puede enviar email.")
            return False
        
        if not all([self.smtp_server, self.smtp_port, self.smtp_user, self.smtp_password, self.smtp_recipient]):
            logger.error("Email no configurado correctamente")
            return False
        
        try:
            # Crear asunto basado en tipo
            subject_map = {
                NotificationType.INFO: "ℹ️ Info",
                NotificationType.SUCCESS: "✅ Éxito",
                NotificationType.WARNING: "⚠️ Advertencia",
                NotificationType.ERROR: "❌ Error",
                NotificationType.TRADE: "💰 Trade",
                NotificationType.OPPORTUNITY: "🎯 Oportunidad"
            }
            subject = f"[BotPolyMarket] {subject_map.get(notification_type, 'Notificación')}: {kwargs.get('subject', 'Sin asunto')}"
            
            # Crear cuerpo del mensaje
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = self.smtp_recipient
            msg['Subject'] = subject
            msg['Date'] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
            
            # Agregar contenido
            body = MIMEText(message, 'plain', 'utf-8')
            msg.attach(body)
            
            # Enviar
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.debug(f"Email enviado a {self.smtp_recipient}")
            return True
            
        except Exception as e:
            logger.error(f"Excepción al enviar email: {e}")
            return False

          def _send_discord(self, message: str, notification_type: NotificationType) -> bool:
        """
        Envía notificación por Discord (Webhook)
        
        Returns:
            True si se envió correctamente
        """
        if not requests:
            logger.error("requests no está instalado. No se puede enviar Discord.")
            return False
        
        if not self.discord_webhook:
            logger.error("Discord webhook no configurado")
            return False
        
        try:
            # Mapeo de colores según tipo
            color_map = {
                NotificationType.INFO: 3447003,  # Azul
                NotificationType.SUCCESS: 3066993,  # Verde
                NotificationType.WARNING: 16776960,  # Amarillo
                NotificationType.ERROR: 15158332,  # Rojo
                NotificationType.TRADE: 10181046,  # Morado
                NotificationType.OPPORTUNITY: 3447003  # Azul
            }
            
            emoji = self._get_emoji(notification_type)
            
            data = {
                "embeds": [{
                    "title": f"{emoji} {notification_type.value.title()}",
                    "description": message,
                    "color": color_map.get(notification_type, 0),
                    "timestamp": datetime.now().isoformat(),
                    "footer": {"text": "BotPolyMarket"}
                }]
            }
            
            response = requests.post(self.discord_webhook, json=data, timeout=10)
            
            if response.status_code == 204:
                logger.debug("Notificación Discord enviada")
                return True
            else:
                logger.error(f"Error enviando Discord: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Excepción al enviar Discord: {e}")
            return False

          def _get_emoji(self, notification_type: NotificationType) -> str:
        """
        Obtiene el emoji correspondiente al tipo de notificación
        
        Returns:
            Emoji como string
        """
        emoji_map = {
            NotificationType.INFO: "ℹ️",
            NotificationType.SUCCESS: "✅",
            NotificationType.WARNING: "⚠️",
            NotificationType.ERROR: "❌",
            NotificationType.TRADE: "💰",
            NotificationType.OPPORTUNITY: "🎯"
        }
        return emoji_map.get(notification_type, "🔔")
