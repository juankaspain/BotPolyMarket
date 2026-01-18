#!/usr/bin/env python3
"""BotPolyMarket - Sistema de Trading Automatizado

Punto de entrada único que integra:
- Copy Trading
- Estrategias GAP (10 estrategias optimizadas)
- Trading Autónomo
- FASE 1: Kelly auto-sizing, WebSockets, APIs externas

Autor: juankaspain
Versión: 6.1 - FASE 1 Integrated
"""
import os
import sys
import logging
import argparse
from dotenv import load_dotenv

load_dotenv()

def setup_logging():
    """Configura el sistema de logging"""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_file = os.getenv('LOG_FILE', 'bot_polymarket.log')
    
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%H:%M:%S',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

def validate_config() -> dict:
    """Valida y construye la configuración del bot"""
    config = {
        'capital': float(os.getenv('YOUR_CAPITAL', '10000')),
        'mode': os.getenv('MODE', 'paper'),  # paper or live
        'polling_interval': int(os.getenv('POLLING_INTERVAL', '60')),
        'private_key': os.getenv('PRIVATE_KEY', ''),
        'api_key': os.getenv('POLYMARKET_API_KEY', ''),
        'binance_api_key': os.getenv('BINANCE_API_KEY', ''),
        'binance_secret': os.getenv('BINANCE_SECRET', ''),
        'kalshi_api_key': os.getenv('KALSHI_API_KEY', ''),
        'enable_websockets': os.getenv('ENABLE_WEBSOCKETS', 'true').lower() == 'true',
        'enable_kelly': os.getenv('ENABLE_KELLY', 'true').lower() == 'true',
        'kelly_fraction': float(os.getenv('KELLY_FRACTION', '0.5')),
    }
    
    errors = []
    
    if config['capital'] <= 0:
        errors.append("YOUR_CAPITAL debe ser mayor a 0")
    
    if config['mode'] == 'live' and not config['private_key']:
        errors.append("PRIVATE_KEY requerida para modo live")
    
    if errors:
        for error in errors:
            logging.error(f"❌ {error}")
        raise ValueError("Configuración inválida")
    
    return config

def display_banner(config):
    """Muestra el banner de bienvenida"""
    print("\n" + "="*80)
    print("🚀 BOTPOLYMARKET v6.1 - FASE 1 OPTIMIZED")
    print("="*80)
    print(f"Mode:          {config['mode'].upper()}")
    print(f"Capital:       ${config['capital']:,.2f}")
    print(f"Kelly:         {'Enabled' if config['enable_kelly'] else 'Disabled'} ({config['kelly_fraction']} fraction)")
    print(f"WebSockets:    {'Enabled' if config['enable_websockets'] else 'Disabled'}")
    print(f"Interval:      {config['polling_interval']}s")
    print("="*80 + "\n")

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='BotPolyMarket v6.1')
    parser.add_argument('--mode', choices=['paper', 'live', 'backtest'], 
                       default=None, help='Trading mode')
    parser.add_argument('--capital', type=float, default=None, 
                       help='Initial capital')
    parser.add_argument('--interval', type=int, default=None, 
                       help='Scan interval (seconds)')
    parser.add_argument('--config', default='config/config.yaml',
                       help='Config file path')
    
    args = parser.parse_args()
    
    # Setup
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Validar config
        logger.info("🔍 Validando configuración...")
        config = validate_config()
        
        # Override con args
        if args.mode:
            config['mode'] = args.mode
        if args.capital:
            config['capital'] = args.capital
        if args.interval:
            config['polling_interval'] = args.interval
        
        logger.info("✅ Configuración válida")
        
        # Banner
        display_banner(config)
        
        # Import orchestrator
        logger.info("🚀 Iniciando BotOrchestrator...")
        from core.orchestrator import BotOrchestrator
        
        orchestrator = BotOrchestrator(config)
        orchestrator.run()
        
    except ValueError as e:
        logger.error(f"❌ Error de configuración: {e}")
        print("\n💡 Solución:")
        print("  1. Copia .env.example a .env")
        print("  2. Configura YOUR_CAPITAL > 0")
        print("  3. Para live mode, configura PRIVATE_KEY\n")
        sys.exit(1)
        
    except ImportError as e:
        logger.error(f"❌ Error importando: {e}")
        print("\n💡 Instala: pip install -r requirements.txt\n")
        sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("\n\n⚠️ Bot interrumpido por el usuario")
        print("\n✅ Bot detenido correctamente\n")
        sys.exit(0)
        
    except Exception as e:
        logger.critical(f"🚫 Error crítico: {e}", exc_info=True)
        print(f"\n❌ Error crítico: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
