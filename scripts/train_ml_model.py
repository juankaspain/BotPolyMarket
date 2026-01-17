#!/usr/bin/env python3
"""
v2.0 ML Gap Predictor - Training Pipeline
Entrena el modelo LSTM con datos históricos de Polymarket
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime, timedelta
from core.ml_gap_predictor import MLGapPredictor
from core.sentiment_analyzer import SentimentAnalyzer
from core.auto_backtest import AutoBacktest
from core.telegram_notifier import TelegramNotifier
from core.database import Database
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MLTrainingPipeline:
    """Pipeline completo para entrenar y validar el modelo ML"""
    
    def __init__(self):
        self.ml_predictor = MLGapPredictor()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.backtest = AutoBacktest()
        self.notifier = TelegramNotifier()
        self.db = Database()
        
    async def collect_historical_data(self, months=6):
        """
        Recolecta 6 meses de datos históricos de Polymarket
        """
        logger.info(f"📊 Recolectando {months} meses de datos históricos...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)
        
        # Aquí conectaríamos con la API de Polymarket para datos históricos
        # Por ahora simulamos la estructura
        historical_data = {
            'markets': [],
            'gaps': [],
            'outcomes': [],
            'sentiment': []
        }
        
        logger.info(f"✅ Datos recolectados: {start_date} a {end_date}")
        return historical_data
    
    async def enrich_with_sentiment(self, market_data):
        """
        Enriquece datos de mercado con análisis de sentimiento
        """
        logger.info("🧠 Analizando sentimiento de noticias y tweets...")
        
        enriched_data = []
        for market in market_data:
            sentiment_score = await self.sentiment_analyzer.analyze_market(market)
            market['sentiment'] = sentiment_score
            enriched_data.append(market)
        
        return enriched_data
    
    async def train_model(self, training_data):
        """
        Entrena el modelo LSTM con los datos preparados
        """
        logger.info("🤖 Entrenando modelo LSTM...")
        
        # Preparar features
        X, y = self.ml_predictor.prepare_features(training_data)
        
        # Entrenar modelo
        history = await self.ml_predictor.train(
            X, y,
            epochs=100,
            batch_size=32,
            validation_split=0.2
        )
        
        # Guardar modelo
        model_path = self.ml_predictor.save_model('models/lstm_gap_predictor_v2.0.h5')
        logger.info(f"💾 Modelo guardado en: {model_path}")
        
        return history
    
    async def run_backtest(self, test_data):
        """
        Ejecuta backtest con los últimos 2 meses de datos
        """
        logger.info("📈 Ejecutando backtest automático...")
        
        results = await self.backtest.run(
            strategy='ml_gap_predictor',
            data=test_data,
            initial_capital=1500  # Capital test según roadmap
        )
        
        logger.info(f"""
        📊 Resultados Backtest:
        - Capital Inicial: {results['initial_capital']}€
        - Capital Final: {results['final_capital']}€
        - ROI: {results['roi']}%
        - Win Rate: {results['win_rate']}%
        - Trades Totales: {results['total_trades']}
        - Sharpe Ratio: {results['sharpe_ratio']}
        """)
        
        return results
    
    async def validate_accuracy(self, validation_data):
        """
        Valida accuracy del modelo (meta: 78% win rate)
        """
        logger.info("🎯 Validando accuracy del modelo...")
        
        predictions = await self.ml_predictor.predict_batch(validation_data)
        accuracy = self.ml_predictor.calculate_accuracy(predictions, validation_data)
        
        logger.info(f"📊 Accuracy obtenida: {accuracy}%")
        
        if accuracy >= 78:
            logger.info("✅ Meta de 78% win rate ALCANZADA!")
        else:
            logger.warning(f"⚠️ Meta no alcanzada. Accuracy: {accuracy}% < 78%")
        
        return accuracy
    
    async def send_completion_report(self, results):
        """
        Envía reporte de completación a Telegram
        """
        report = f"""
🚀 v2.0 ML Gap Predictor - COMPLETADO

📊 Métricas de Entrenamiento:
• Accuracy: {results['accuracy']}%
• Win Rate: {results['win_rate']}%
• ROI Proyectado: {results['roi']}%

💰 Backtest Results:
• Capital Inicial: {results['initial_capital']}€
• Capital Final: {results['final_capital']}€
• Ganancia: {results['profit']}€

🎯 Estado: {'✅ LISTO PARA PRODUCCIÓN' if results['accuracy'] >= 78 else '⚠️ REQUIERE OPTIMIZACIÓN'}

📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        """
        
        await self.notifier.send_message(report)
        logger.info("📱 Reporte enviado a Telegram")
    
    async def execute_full_pipeline(self):
        """
        Ejecuta el pipeline completo de entrenamiento v2.0
        """
        try:
            logger.info("🚀 Iniciando pipeline de entrenamiento v2.0...")
            
            # 1. Recolectar datos históricos (6 meses)
            historical_data = await self.collect_historical_data(months=6)
            
            # 2. Enriquecer con sentiment analysis
            enriched_data = await self.enrich_with_sentiment(historical_data)
            
            # 3. Dividir en train/test (80/20)
            split_idx = int(len(enriched_data) * 0.8)
            train_data = enriched_data[:split_idx]
            test_data = enriched_data[split_idx:]
            
            # 4. Entrenar modelo LSTM
            training_history = await self.train_model(train_data)
            
            # 5. Validar accuracy
            accuracy = await self.validate_accuracy(test_data)
            
            # 6. Ejecutar backtest
            backtest_results = await self.run_backtest(test_data)
            
            # 7. Compilar resultados
            final_results = {
                'accuracy': accuracy,
                'win_rate': backtest_results['win_rate'],
                'roi': backtest_results['roi'],
                'initial_capital': 1500,
                'final_capital': backtest_results['final_capital'],
                'profit': backtest_results['final_capital'] - 1500
            }
            
            # 8. Enviar reporte a Telegram
            await self.send_completion_report(final_results)
            
            logger.info("✅ Pipeline v2.0 completado exitosamente!")
            return final_results
            
        except Exception as e:
            logger.error(f"❌ Error en pipeline: {e}", exc_info=True)
            await self.notifier.send_message(f"❌ Error en entrenamiento v2.0: {e}")
            raise

if __name__ == "__main__":
    pipeline = MLTrainingPipeline()
    results = asyncio.run(pipeline.execute_full_pipeline())
    print(f"\n✅ Entrenamiento completado. Resultados: {results}")
