#!/usr/bin/env python3
"""
Script para ejecutar backtest automático
Usage: python scripts/run_backtest.py
"""
import sys
import os
import logging
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.auto_backtest import AutoBacktestEngine

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """
    Ejecuta backtest automático de 6 meses
    """
    # Load config
    load_dotenv()
    
    config = {
        'backtest_capital': float(os.getenv('BACKTEST_CAPITAL', '1500')),
        'backtest_lookback_days': int(os.getenv('BACKTEST_LOOKBACK_DAYS', '180')),
        'sequence_length': int(os.getenv('ML_SEQUENCE_LENGTH', '30')),
        'prediction_threshold': float(os.getenv('ML_PREDICTION_THRESHOLD', '0.78')),
        'model_path': 'models/lstm_gap_predictor.h5',
        'scaler_path': 'models/scaler.pkl',
        'backtest_data_path': 'data/backtest_data.csv',
        'cryptocompare_api_key': os.getenv('CRYPTOCOMPARE_API_KEY', ''),
        'polymarket_api_key': os.getenv('POLYMARKET_API_KEY', '')
    }
    
    logger.info("🚀 Iniciando Auto Backtest v2.0...")
    logger.info(f"💰 Capital inicial: ${config['backtest_capital']:,.2f}")
    logger.info(f"📅 Lookback: {config['backtest_lookback_days']} días")
    
    # Create engine
    engine = AutoBacktestEngine(config)
    
    # Run backtest
    try:
        report = engine.run_backtest(train_test_split=0.8)
        
        # Print report
        engine.print_report(report)
        
        # Check targets
        if report['targets']['win_rate_achieved'] and report['targets']['roi_achieved']:
            logger.info("\n🎉 ¡TODOS LOS TARGETS DE v2.0 ALCANZADOS!")
        else:
            logger.warning("\n⚠️ Algunos targets no fueron alcanzados. Revisar modelo.")
    
    except Exception as e:
        logger.error(f"❌ Error ejecutando backtest: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
