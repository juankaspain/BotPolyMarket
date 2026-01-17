#!/usr/bin/env python3
"""
BotPolyMarket - Sistema de Trading Automatizado Unificado

Punto de entrada único que integra:
- Copy Trading (replica traders exitosos)
- Estrategias GAP (10 estrategias de elite)
- Trading Autónomo (momentum, value betting)
- Dashboard de monitoreo

Autor: juankaspain
Versión: 2.0 - Arquitectura Unificada
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def setup_logging():
    """Configura el sistema de logging"""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_file = os.getenv('LOG_FILE', 'bot_polymarket.log')
    
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reducir verbosidad de librerías externas
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

def validate_config() -> dict:
    """Valida y construye la configuración del bot"""
    config = {
        'capital': float(os.getenv('YOUR_CAPITAL', '1000')),
        'trader_address': os.getenv('TRADER_ADDRESS', ''),
        'private_key': os.getenv('PRIVATE_KEY', ''),
        'api_key': os.getenv('POLYMARKET_API_KEY', ''),
        'mode': os.getenv('MODE', 'monitor'),
        'polling_interval': int(os.getenv('POLLING_INTERVAL', '30')),
        'database_path': os.getenv('DATABASE_PATH', 'bot_polymarket.db'),
        'wallet_address': os.getenv('WALLET_ADDRESS', ''),
    }
    
    errors = []
    
    if config['capital'] <= 0:
        errors.append("YOUR_CAPITAL debe ser mayor a 0")
    
    if config['mode'] == 'execute' and not config['private_key']:
        errors.append("PRIVATE_KEY requerida para modo execute")
    
    if errors:
        for error in errors:
            logging.error(f"❌ {error}")
        raise ValueError("Configuración inválida")
    
    return config

def display_banner():
    """Muestra el banner de bienvenida"""
    banner = """
╭──────────────────────────────────────────────────────────────────────╮
│         🤖 BOTPOLYMARKET v2.0 - ARQUITECTURA UNIFICADA        │
│               Sistema de Trading Automatizado                 │
╰──────────────────────────────────────────────────────────────────────╯
    """
    print(banner)

def main():
    """Función principal - Punto de entrada único"""
    # Configurar logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Mostrar banner
        display_banner()
        
        # Validar configuración
        logger.info("🔍 Validando configuración...")
        config = validate_config()
        logger.info("✅ Configuración válida")
        
        # Importar y ejecutar orquestador
        logger.info("🚀 Iniciando BotOrchestrator...")
        from core.orchestrator import BotOrchestrator
        
        orchestrator = BotOrchestrator(config)
        orchestrator.run()
        
    except ValueError as e:
        logger.error(f"❌ Error de configuración: {e}")
        print("\n💡 Solución:")
        print("  1. Copia .env.example a .env")
        print("  2. Configura las variables necesarias")
        print("  3. Asegúrate de que YOUR_CAPITAL > 0")
        print("  4. Para modo execute, configura PRIVATE_KEY\n")
        sys.exit(1)
    except ImportError as e:
        logger.error(f"❌ Error importando módulos: {e}")
        print("\n💡 Solución:")
        print("  1. Instala las dependencias: pip install -r requirements.txt")
        print("  2. Verifica que estés en el directorio correcto\n")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n\n⚠️ Bot interrumpido por el usuario")
        print("\n✅ Bot detenido correctamente\n")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"🚫 Error crítico: {e}", exc_info=True)
        print(f"\n❌ Error crítico: {e}")
        print("🛠️ Revisa el archivo de log para más detalles\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
