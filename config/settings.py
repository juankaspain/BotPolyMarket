"""Gestión de configuración del bot desde variables de entorno"""
import os
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

class Settings:
    """Configuración centralizada del bot"""
    
    # ==================== API CREDENTIALS ====================
    POLYMARKET_API_KEY: str = os.getenv('POLYMARKET_API_KEY', '')
    PRIVATE_KEY: str = os.getenv('PRIVATE_KEY', '')
    WALLET_ADDRESS: str = os.getenv('WALLET_ADDRESS', '')
    
    # ==================== BOT CONFIGURATION ====================
    TRADING_MODE: str = os.getenv('TRADING_MODE', 'paper')  # 'live' o 'paper'
    UPDATE_INTERVAL: int = int(os.getenv('UPDATE_INTERVAL', '60'))
    INITIAL_CAPITAL: float = float(os.getenv('INITIAL_CAPITAL', '1000'))
    
    # ==================== RISK MANAGEMENT ====================
    MAX_POSITION_SIZE: float = float(os.getenv('MAX_POSITION_SIZE', '0.05'))
    MAX_TOTAL_EXPOSURE: float = float(os.getenv('MAX_TOTAL_EXPOSURE', '0.30'))
    DEFAULT_STOP_LOSS: float = float(os.getenv('DEFAULT_STOP_LOSS', '0.08'))
    DEFAULT_TAKE_PROFIT: float = float(os.getenv('DEFAULT_TAKE_PROFIT', '0.15'))
    
    # ==================== ESTRATEGIAS ====================
    ACTIVE_STRATEGIES: List[str] = os.getenv(
        'ACTIVE_STRATEGIES', 
        'momentum,value_betting'
    ).split(',')
    
    # Momentum Strategy
    MOMENTUM_PRICE_THRESHOLD: float = float(os.getenv('MOMENTUM_PRICE_THRESHOLD', '0.05'))
    MOMENTUM_VOLUME_THRESHOLD: int = int(os.getenv('MOMENTUM_VOLUME_THRESHOLD', '1000'))
    
    # Value Betting Strategy
    VALUE_MIN_EDGE: float = float(os.getenv('VALUE_MIN_EDGE', '0.05'))
    VALUE_KELLY_FRACTION: float = float(os.getenv('VALUE_KELLY_FRACTION', '0.25'))
    VALUE_MIN_LIQUIDITY: int = int(os.getenv('VALUE_MIN_LIQUIDITY', '5000'))
    
    # ==================== DATABASE ====================
    DATABASE_URL: str = os.getenv(
        'DATABASE_URL', 
        'sqlite:///polymarket_bot.db'
    )
    
    # ==================== LOGGING ====================
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_DIR: str = os.getenv('LOG_DIR', 'logs')
    LOG_FORMAT: str = os.getenv('LOG_FORMAT', 'text')  # 'json' o 'text'
    
    # ==================== NOTIFICATIONS ====================
    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID: Optional[str] = os.getenv('TELEGRAM_CHAT_ID')
    NOTIFICATION_EMAIL: Optional[str] = os.getenv('NOTIFICATION_EMAIL')
    
    # ==================== ADVANCED SETTINGS ====================
    API_TIMEOUT: int = int(os.getenv('API_TIMEOUT', '30'))
    MAX_RETRIES: int = int(os.getenv('MAX_RETRIES', '3'))
    ENABLE_CACHE: bool = os.getenv('ENABLE_CACHE', 'true').lower() == 'true'
    CACHE_TTL: int = int(os.getenv('CACHE_TTL', '300'))
    
    @classmethod
    def validate(cls) -> List[str]:
        """Valida que todas las configuraciones críticas estén presentes
        
        Returns:
            Lista de errores de validación (vacía si todo OK)
        """
        errors = []
        
        # Validar API credentials solo en modo live
        if cls.TRADING_MODE == 'live':
            if not cls.POLYMARKET_API_KEY:
                errors.append("POLYMARKET_API_KEY es obligatorio en modo live")
            if not cls.PRIVATE_KEY:
                errors.append("PRIVATE_KEY es obligatorio en modo live")
            if not cls.WALLET_ADDRESS:
                errors.append("WALLET_ADDRESS es obligatorio en modo live")
        
        # Validar rangos de valores
        if not 0 < cls.MAX_POSITION_SIZE <= 1:
            errors.append("MAX_POSITION_SIZE debe estar entre 0 y 1")
        
        if not 0 < cls.MAX_TOTAL_EXPOSURE <= 1:
            errors.append("MAX_TOTAL_EXPOSURE debe estar entre 0 y 1")
        
        if cls.INITIAL_CAPITAL <= 0:
            errors.append("INITIAL_CAPITAL debe ser positivo")
        
        if cls.UPDATE_INTERVAL < 1:
            errors.append("UPDATE_INTERVAL debe ser al menos 1 segundo")
        
        # Validar modo de trading
        if cls.TRADING_MODE not in ['live', 'paper']:
            errors.append("TRADING_MODE debe ser 'live' o 'paper'")
        
        # Validar estrategias
        valid_strategies = ['momentum', 'value_betting', 'arbitrage']
        for strategy in cls.ACTIVE_STRATEGIES:
            if strategy.strip() not in valid_strategies:
                errors.append(f"Estrategia inválida: {strategy}")
        
        return errors
    
    @classmethod
    def print_config(cls):
        """Imprime la configuración actual (sin secretos)"""
        print("="*60)
        print("CONFIGURACIÓN DEL BOT POLYMARKET")
        print("="*60)
        print(f"Modo de trading: {cls.TRADING_MODE}")
        print(f"Capital inicial: ${cls.INITIAL_CAPITAL:,.2f}")
        print(f"Intervalo de actualización: {cls.UPDATE_INTERVAL}s")
        print(f"\nGESTIÓN DE RIESGO:")
        print(f"  - Máx. posición: {cls.MAX_POSITION_SIZE*100}%")
        print(f"  - Máx. exposición: {cls.MAX_TOTAL_EXPOSURE*100}%")
        print(f"  - Stop loss: {cls.DEFAULT_STOP_LOSS*100}%")
        print(f"  - Take profit: {cls.DEFAULT_TAKE_PROFIT*100}%")
        print(f"\nESTRATEGIAS ACTIVAS: {', '.join(cls.ACTIVE_STRATEGIES)}")
        print(f"\nLOGGING:")
        print(f"  - Nivel: {cls.LOG_LEVEL}")
        print(f"  - Directorio: {cls.LOG_DIR}")
        print(f"  - Formato: {cls.LOG_FORMAT}")
        print(f"\nBASE DE DATOS: {cls.DATABASE_URL}")
        
        # Validación
        errors = cls.validate()
        if errors:
            print(f"\n⚠️  ERRORES DE CONFIGURACIÓN:")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"\n✅ Configuración válida")
        
        print("="*60)
    
    @classmethod
    def get_strategy_config(cls, strategy_name: str) -> dict:
        """Obtiene la configuración específica de una estrategia
        
        Args:
            strategy_name: Nombre de la estrategia
            
        Returns:
            Diccionario con la configuración de la estrategia
        """
        if strategy_name == 'momentum':
            return {
                'price_threshold': cls.MOMENTUM_PRICE_THRESHOLD,
                'volume_threshold': cls.MOMENTUM_VOLUME_THRESHOLD,
                'take_profit': cls.DEFAULT_TAKE_PROFIT,
                'stop_loss': cls.DEFAULT_STOP_LOSS
            }
        elif strategy_name == 'value_betting':
            return {
                'min_edge': cls.VALUE_MIN_EDGE,
                'kelly_fraction': cls.VALUE_KELLY_FRACTION,
                'min_liquidity': cls.VALUE_MIN_LIQUIDITY,
                'max_bet_size': cls.INITIAL_CAPITAL * cls.MAX_POSITION_SIZE
            }
        else:
            return {}

# Instancia global de configuración
settings = Settings()

# Validar al importar
if __name__ != '__main__':
    validation_errors = settings.validate()
    if validation_errors:
        import warnings
        for error in validation_errors:
            warnings.warn(f"Error de configuración: {error}")

if __name__ == '__main__':
    # Prueba de configuración
    settings.print_config()
