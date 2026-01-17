"""validators.py
Sistema de Validación Robusto para BotPolyMarket

Proporciona validación completa de:
- Direcciones wallet Ethereum
- Configuración del bot
- Inputs de usuario
- Parámetros de trading

Autor: juankaspain
"""

import re
import logging
from typing import Optional, Tuple, Any
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Excepción personalizada para errores de validación"""
    pass


class Validators:
    """
    Clase estática con métodos de validación
    """
    
    @staticmethod
    def validate_ethereum_address(address: str) -> Tuple[bool, Optional[str]]:
        """
        Valida una dirección Ethereum
        
        Args:
            address: Dirección wallet a validar
        
        Returns:
            Tuple[bool, Optional[str]]: (es_valida, mensaje_error)
        """
        if not address:
            return False, "La dirección no puede estar vacía"
        
        # Remover espacios
        address = address.strip()
        
        # Verificar formato básico: 0x seguido de 40 caracteres hexadecimales
        if not re.match(r'^0x[a-fA-F0-9]{40}$', address):
            return False, "Formato de dirección Ethereum inválido. Debe ser 0x seguido de 40 caracteres hexadecimales"
        
        logger.info(f"✅ Dirección Ethereum válida: {address[:10]}...{address[-8:]}")
        return True, None
    
    @staticmethod
    def validate_positive_number(value: Any, name: str, min_value: float = 0) -> Tuple[bool, Optional[str]]:
        """
        Valida que un valor sea un número positivo
        
        Args:
            value: Valor a validar
            name: Nombre del campo para mensajes de error
            min_value: Valor mínimo permitido
        
        Returns:
            Tuple[bool, Optional[str]]: (es_valido, mensaje_error)
        """
        try:
            num = float(value)
            if num < min_value:
                return False, f"{name} debe ser mayor o igual a {min_value}"
            logger.debug(f"✅ {name} válido: {num}")
            return True, None
        except (ValueError, TypeError):
            return False, f"{name} debe ser un número válido"
    
    @staticmethod
    def validate_percentage(value: Any, name: str) -> Tuple[bool, Optional[str]]:
        """
        Valida que un valor sea un porcentaje válido (0-100)
        
        Args:
            value: Valor a validar
            name: Nombre del campo
        
        Returns:
            Tuple[bool, Optional[str]]: (es_valido, mensaje_error)
        """
        try:
            num = float(value)
            if num < 0 or num > 100:
                return False, f"{name} debe estar entre 0 y 100"
            logger.debug(f"✅ {name} válido: {num}%")
            return True, None
        except (ValueError, TypeError):
            return False, f"{name} debe ser un número válido"
    
    @staticmethod
    def validate_decimal_places(value: Any, max_decimals: int, name: str) -> Tuple[bool, Optional[str]]:
        """
        Valida el número de decimales de un valor
        
        Args:
            value: Valor a validar
            max_decimals: Número máximo de decimales permitidos
            name: Nombre del campo
        
        Returns:
            Tuple[bool, Optional[str]]: (es_valido, mensaje_error)
        """
        try:
            dec = Decimal(str(value))
            if abs(dec.as_tuple().exponent) > max_decimals:
                return False, f"{name} no puede tener más de {max_decimals} decimales"
            return True, None
        except (InvalidOperation, ValueError):
            return False, f"{name} debe ser un número válido"
    
    @staticmethod
    def validate_api_key(api_key: str, key_type: str = "API") -> Tuple[bool, Optional[str]]:
        """
        Valida una API key básica
        
        Args:
            api_key: La API key a validar
            key_type: Tipo de key para mensajes
        
        Returns:
            Tuple[bool, Optional[str]]: (es_valida, mensaje_error)
        """
        if not api_key:
            return False, f"{key_type} key no puede estar vacía"
        
        api_key = api_key.strip()
        
        # Mínimo 32 caracteres para considerarla segura
        if len(api_key) < 32:
            return False, f"{key_type} key debe tener al menos 32 caracteres"
        
        logger.info(f"✅ {key_type} key válida")
        return True, None
    
    @staticmethod
    def validate_config_dict(config: dict, required_keys: list) -> Tuple[bool, Optional[str]]:
        """
        Valida que un diccionario de configuración tenga todas las keys requeridas
        
        Args:
            config: Diccionario de configuración
            required_keys: Lista de keys requeridas
        
        Returns:
            Tuple[bool, Optional[str]]: (es_valido, mensaje_error)
        """
        if not isinstance(config, dict):
            return False, "La configuración debe ser un diccionario"
        
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            return False, f"Faltan las siguientes keys en la configuración: {', '.join(missing_keys)}"
        
        logger.debug("✅ Configuración válida con todas las keys requeridas")
        return True, None
    
    @staticmethod
    def validate_url(url: str, name: str = "URL") -> Tuple[bool, Optional[str]]:
        """
        Valida una URL básica
        
        Args:
            url: URL a validar
            name: Nombre del campo
        
        Returns:
            Tuple[bool, Optional[str]]: (es_valida, mensaje_error)
        """
        if not url:
            return False, f"{name} no puede estar vacía"
        
        url = url.strip()
        
        # Validar formato básico de URL
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        if not re.match(url_pattern, url, re.IGNORECASE):
            return False, f"{name} tiene formato inválido. Debe comenzar con http:// o https://"
        
        logger.debug(f"✅ {name} válida: {url}")
        return True, None
    
    @staticmethod
    def validate_market_id(market_id: str) -> Tuple[bool, Optional[str]]:
        """
        Valida un Market ID de Polymarket
        
        Args:
            market_id: Market ID a validar
        
        Returns:
            Tuple[bool, Optional[str]]: (es_valido, mensaje_error)
        """
        if not market_id:
            return False, "Market ID no puede estar vacío"
        
        market_id = market_id.strip()
        
        # Polymarket usa IDs hexadecimales de 64 caracteres (con 0x)
        if not re.match(r'^0x[a-fA-F0-9]{64}$', market_id):
            return False, "Market ID inválido. Debe ser un hash hexadecimal de 66 caracteres (0x + 64 caracteres)"
        
        logger.debug(f"✅ Market ID válido: {market_id[:10]}...{market_id[-8:]}")
        return True, None
    
    @staticmethod
    def validate_interval(interval: str) -> Tuple[bool, Optional[str]]:
        """
        Valida un intervalo de tiempo
        
        Args:
            interval: Intervalo a validar (ej: '1m', '5m', '1h')
        
        Returns:
            Tuple[bool, Optional[str]]: (es_valido, mensaje_error)
        """
        if not interval:
            return False, "Intervalo no puede estar vacío"
        
        valid_intervals = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
        if interval not in valid_intervals:
            return False, f"Intervalo inválido. Debe ser uno de: {', '.join(valid_intervals)}"
        
        logger.debug(f"✅ Intervalo válido: {interval}")
        return True, None


def validate_and_raise(condition: bool, error_message: str):
    """
    Helper para validar y lanzar excepción si falla
    
    Args:
        condition: Condición que debe ser True
        error_message: Mensaje de error si falla
    
    Raises:
        ValidationError: Si condition es False
    """
    if not condition:
        logger.error(f"❌ Error de validación: {error_message}")
        raise ValidationError(error_message)


def validate_bot_config(config: dict) -> Tuple[bool, list]:
    """
    Valida la configuración completa del bot
    
    Args:
        config: Diccionario con la configuración del bot
    
    Returns:
        Tuple[bool, list]: (es_valida, lista_de_errores)
    """
    errors = []
    
    # Validar dirección wallet
    if 'WALLET_ADDRESS' in config:
        is_valid, error = Validators.validate_ethereum_address(config['WALLET_ADDRESS'])
        if not is_valid:
            errors.append(f"WALLET_ADDRESS: {error}")
    
    # Validar API key de Polymarket
    if 'POLYMARKET_API_KEY' in config:
        is_valid, error = Validators.validate_api_key(config['POLYMARKET_API_KEY'], 'POLYMARKET')
        if not is_valid:
            errors.append(f"POLYMARKET_API_KEY: {error}")
    
    # Validar CLOB URL
    if 'CLOB_URL' in config:
        is_valid, error = Validators.validate_url(config['CLOB_URL'], 'CLOB_URL')
        if not is_valid:
            errors.append(f"CLOB_URL: {error}")
    
    # Validar intervalo de polling
    if 'POLLING_INTERVAL' in config:
        is_valid, error = Validators.validate_positive_number(
            config['POLLING_INTERVAL'], 
            'POLLING_INTERVAL',
            min_value=1
        )
        if not is_valid:
            errors.append(f"POLLING_INTERVAL: {error}")
    
    # Validar modo
    if 'MODE' in config:
        valid_modes = ['monitor', 'execute']
        if config['MODE'] not in valid_modes:
            errors.append(f"MODE: Debe ser uno de {valid_modes}")
    
    # Validar parámetros de riesgo si están presentes
    if 'MAX_POSITION_SIZE' in config:
        is_valid, error = Validators.validate_positive_number(
            config['MAX_POSITION_SIZE'],
            'MAX_POSITION_SIZE',
            min_value=0.01
        )
        if not is_valid:
            errors.append(f"MAX_POSITION_SIZE: {error}")
    
    if 'MAX_DAILY_TRADES' in config:
        is_valid, error = Validators.validate_positive_number(
            config['MAX_DAILY_TRADES'],
            'MAX_DAILY_TRADES',
            min_value=1
        )
        if not is_valid:
            errors.append(f"MAX_DAILY_TRADES: {error}")
    
    if 'MIN_LIQUIDITY' in config:
        is_valid, error = Validators.validate_positive_number(
            config['MIN_LIQUIDITY'],
            'MIN_LIQUIDITY',
            min_value=0
        )
        if not is_valid:
            errors.append(f"MIN_LIQUIDITY: {error}")
    
    is_valid = len(errors) == 0
    
    if is_valid:
        logger.info("✅ Configuración validada correctamente")
    else:
        logger.error(f"❌ Errores de validación: {len(errors)}")
        for error in errors:
            logger.error(f"  - {error}")
    
    return is_valid, errors
