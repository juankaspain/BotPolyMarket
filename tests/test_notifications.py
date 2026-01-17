"""Tests para el sistema de notificaciones

Tests unitarios completos para NotificationSystem que cubren:
- Inicialización del sistema
- Envío de notificaciones por Telegram
- Envío de notificaciones por Email
- Envío de notificaciones por Discord
- Sistema de fallback
- Manejo de errores

Autor: juankaspain
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.notifications import NotificationSystem, NotificationType


class TestNotificationSystem(unittest.TestCase):
    """Tests para NotificationSystem"""
    
    def setUp(self):
        """Configuración antes de cada test"""
        self.config = {
            'telegram_token': 'test_token_123',
            'telegram_chat_id': '123456789',
            'smtp_server': 'smtp.test.com',
            'smtp_port': 587,
            'smtp_user': 'test@test.com',
            'smtp_password': 'test_password',
            'smtp_recipient': 'recipient@test.com',
            'discord_webhook': 'https://discord.com/api/webhooks/test'
        }
        self.notification_system = NotificationSystem(self.config)
    
    def test_initialization(self):
        """Test: Sistema se inicializa correctamente"""
        self.assertIsNotNone(self.notification_system)
        self.assertTrue(self.notification_system.telegram_enabled)
        self.assertTrue(self.notification_system.email_enabled)
        self.assertTrue(self.notification_system.discord_enabled)
    
    def test_initialization_without_telegram(self):
        """Test: Sistema se inicializa sin Telegram"""
        config = self.config.copy()
        config['telegram_token'] = None
        ns = NotificationSystem(config)
        self.assertFalse(ns.telegram_enabled)
    
    def test_initialization_without_email(self):
        """Test: Sistema se inicializa sin Email"""
        config = self.config.copy()
        config['smtp_user'] = None
        ns = NotificationSystem(config)
        self.assertFalse(ns.email_enabled)
    
    def test_initialization_without_discord(self):
        """Test: Sistema se inicializa sin Discord"""
        config = self.config.copy()
        config['discord_webhook'] = None
        ns = NotificationSystem(config)
        self.assertFalse(ns.discord_enabled)
    
    @patch('utils.notifications.requests')
    def test_send_telegram_success(self, mock_requests):
        """Test: Envío exitoso de notificación por Telegram"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_requests.post.return_value = mock_response
        
        result = self.notification_system._send_telegram(
            "Test message",
            NotificationType.INFO
        )
        
        self.assertTrue(result)
        mock_requests.post.assert_called_once()
    
    @patch('utils.notifications.requests')
    def test_send_telegram_failure(self, mock_requests):
        """Test: Fallo en envío por Telegram"""
        # Mock response con error
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = 'Error'
        mock_requests.post.return_value = mock_response
        
        result = self.notification_system._send_telegram(
            "Test message",
            NotificationType.ERROR
        )
        
        self.assertFalse(result)
    
    @patch('utils.notifications.requests')
    def test_send_telegram_exception(self, mock_requests):
        """Test: Excepción al enviar por Telegram"""
        mock_requests.post.side_effect = Exception("Connection error")
        
        result = self.notification_system._send_telegram(
            "Test message",
            NotificationType.WARNING
        )
        
        self.assertFalse(result)
    
    @patch('utils.notifications.smtplib')
    def test_send_email_success(self, mock_smtplib):
        """Test: Envío exitoso de notificación por Email"""
        # Mock SMTP server
        mock_server = MagicMock()
        mock_smtplib.SMTP.return_value.__enter__.return_value = mock_server
        
        result = self.notification_system._send_email(
            "Test message",
            NotificationType.SUCCESS,
            subject="Test Subject"
        )
        
        self.assertTrue(result)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()
    
    @patch('utils.notifications.smtplib')
    def test_send_email_exception(self, mock_smtplib):
        """Test: Excepción al enviar por Email"""
        mock_smtplib.SMTP.side_effect = Exception("SMTP error")
        
        result = self.notification_system._send_email(
            "Test message",
            NotificationType.ERROR,
            subject="Test Subject"
        )
        
        self.assertFalse(result)
    
    @patch('utils.notifications.requests')
    def test_send_discord_success(self, mock_requests):
        """Test: Envío exitoso de notificación por Discord"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 204
        mock_requests.post.return_value = mock_response
        
        result = self.notification_system._send_discord(
            "Test message",
            NotificationType.TRADE
        )
        
        self.assertTrue(result)
        mock_requests.post.assert_called_once()
    
    @patch('utils.notifications.requests')
    def test_send_discord_failure(self, mock_requests):
        """Test: Fallo en envío por Discord"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_requests.post.return_value = mock_response
        
        result = self.notification_system._send_discord(
            "Test message",
            NotificationType.OPPORTUNITY
        )
        
        self.assertFalse(result)
    
    def test_get_emoji(self):
        """Test: Obtención de emojis correctos"""
        emoji_info = self.notification_system._get_emoji(NotificationType.INFO)
        self.assertEqual(emoji_info, "ℹ️")
        
        emoji_success = self.notification_system._get_emoji(NotificationType.SUCCESS)
        self.assertEqual(emoji_success, "✅")
        
        emoji_warning = self.notification_system._get_emoji(NotificationType.WARNING)
        self.assertEqual(emoji_warning, "⚠️")
        
        emoji_error = self.notification_system._get_emoji(NotificationType.ERROR)
        self.assertEqual(emoji_error, "❌")
    
    @patch('utils.notifications.requests')
    @patch('utils.notifications.smtplib')
    def test_send_all_channels(self, mock_smtplib, mock_requests):
        """Test: Envío a todos los canales"""
        # Mock successful responses
        mock_response_telegram = Mock()
        mock_response_telegram.status_code = 200
        
        mock_response_discord = Mock()
        mock_response_discord.status_code = 204
        
        mock_requests.post.side_effect = [mock_response_telegram, mock_response_discord]
        
        mock_server = MagicMock()
        mock_smtplib.SMTP.return_value.__enter__.return_value = mock_server
        
        result = self.notification_system.send(
            "Test notification",
            NotificationType.INFO
        )
        
        # Debe intentar enviar a todos los canales
        self.assertEqual(mock_requests.post.call_count, 2)  # Telegram + Discord
    
    @patch('utils.notifications.requests')
    def test_send_with_only_telegram_enabled(self, mock_requests):
        """Test: Envío solo con Telegram habilitado"""
        # Deshabilitar otros canales
        self.notification_system.email_enabled = False
        self.notification_system.discord_enabled = False
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_requests.post.return_value = mock_response
        
        result = self.notification_system.send(
            "Test message",
            NotificationType.SUCCESS
        )
        
        mock_requests.post.assert_called_once()
    
    def test_send_without_enabled_channels(self):
        """Test: Envío sin canales habilitados"""
        self.notification_system.telegram_enabled = False
        self.notification_system.email_enabled = False
        self.notification_system.discord_enabled = False
        
        result = self.notification_system.send(
            "Test message",
            NotificationType.WARNING
        )
        
        # No debe fallar, simplemente no envía nada
        # El comportamiento esperado es que no haga nada


class TestNotificationType(unittest.TestCase):
    """Tests para NotificationType enum"""
    
    def test_notification_types_exist(self):
        """Test: Todos los tipos de notificación existen"""
        self.assertIsNotNone(NotificationType.INFO)
        self.assertIsNotNone(NotificationType.SUCCESS)
        self.assertIsNotNone(NotificationType.WARNING)
        self.assertIsNotNone(NotificationType.ERROR)
        self.assertIsNotNone(NotificationType.TRADE)
        self.assertIsNotNone(NotificationType.OPPORTUNITY)
    
    def test_notification_type_values(self):
        """Test: Valores de tipos de notificación"""
        self.assertEqual(NotificationType.INFO.value, 'info')
        self.assertEqual(NotificationType.SUCCESS.value, 'success')
        self.assertEqual(NotificationType.WARNING.value, 'warning')
        self.assertEqual(NotificationType.ERROR.value, 'error')
        self.assertEqual(NotificationType.TRADE.value, 'trade')
        self.assertEqual(NotificationType.OPPORTUNITY.value, 'opportunity')


if __name__ == '__main__':
    unittest.main()
