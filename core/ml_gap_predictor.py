#!/usr/bin/env python3
"""
ML Gap Predictor v2.0
LSTM-based gap prediction with sentiment analysis integration
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import pickle
import os

try:
    from tensorflow import keras
    from keras.models import Sequential, load_model
    from keras.layers import LSTM, Dense, Dropout, BatchNormalization
    from keras.callbacks import EarlyStopping, ModelCheckpoint
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.model_selection import train_test_split
    KERAS_AVAILABLE = True
except ImportError:
    KERAS_AVAILABLE = False
    logging.warning("TensorFlow/Keras not available. Install with: pip install tensorflow keras")

from utils.sentiment_analyzer import SentimentAnalyzer

logger = logging.getLogger(__name__)

class MLGapPredictor:
    """
    Predictor de gaps usando LSTM + Sentiment Analysis
    
    Features:
    - LSTM para series temporales de gaps
    - Sentiment analysis de news/crypto tweets
    - Auto-backtest de 6 meses de data de Polymarket
    - Accuracy target: 78% win rate (+25% vs v1.0)
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.model = None
        self.scaler = MinMaxScaler()
        self.sentiment_analyzer = SentimentAnalyzer(config)
        self.model_path = config.get('model_path', 'models/lstm_gap_predictor.h5')
        self.scaler_path = config.get('scaler_path', 'models/scaler.pkl')
        self.sequence_length = config.get('sequence_length', 30)  # 30 gaps históricos
        self.prediction_threshold = config.get('prediction_threshold', 0.78)  # 78% confidence
        
        # Crear directorio de modelos si no existe
        os.makedirs('models', exist_ok=True)
        
        # Cargar modelo si existe
        if os.path.exists(self.model_path):
            self.load_model()
        else:
            logger.warning("⚠️ No hay modelo entrenado. Ejecuta train() primero.")
    
    def build_model(self, input_shape: Tuple[int, int]) -> keras.Model:
        """
        Construye arquitectura LSTM
        
        Arquitectura:
        - LSTM(128) + Dropout(0.2) + BatchNorm
        - LSTM(64) + Dropout(0.2)
        - Dense(32) + ReLU
        - Dense(1) + Sigmoid (probabilidad de gap exitoso)
        """
        if not KERAS_AVAILABLE:
            raise ImportError("TensorFlow/Keras no disponible")
        
        model = Sequential([
            LSTM(128, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            BatchNormalization(),
            
            LSTM(64, return_sequences=False),
            Dropout(0.2),
            
            Dense(32, activation='relu'),
            Dropout(0.1),
            
            Dense(1, activation='sigmoid')  # Probabilidad [0,1]
        ])
        
        model.compile(
            optimizer='adam',
            loss='binary_crossentropy',
            metrics=['accuracy', 'AUC']
        )
        
        logger.info("✅ Modelo LSTM construido")
        model.summary(print_fn=logger.info)
        
        return model
    
    def prepare_features(self, gaps_data: pd.DataFrame) -> pd.DataFrame:
        """
        Prepara features para el modelo
        
        Features:
        - gap_size: Tamaño del gap (¢)
        - volume: Volumen del mercado
        - liquidity: Liquidez disponible
        - sentiment_score: Score de sentiment [-1, 1]
        - market_momentum: Momentum del mercado
        - time_features: Hora del día, día de la semana
        """
        df = gaps_data.copy()
        
        # Features básicos
        df['gap_size_norm'] = np.abs(df['gap_size'])
        df['volume_log'] = np.log1p(df['volume'])
        df['liquidity_log'] = np.log1p(df['liquidity'])
        
        # Sentiment features
        if 'market_slug' in df.columns:
            df['sentiment_score'] = df['market_slug'].apply(
                lambda x: self.sentiment_analyzer.get_market_sentiment(x)
            )
        else:
            df['sentiment_score'] = 0.0
        
        # Time features
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.dayofweek
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        
        # Market momentum (rolling windows)
        df['gap_size_ma_5'] = df['gap_size_norm'].rolling(5, min_periods=1).mean()
        df['gap_size_std_5'] = df['gap_size_norm'].rolling(5, min_periods=1).std()
        df['success_rate_10'] = df['success'].rolling(10, min_periods=1).mean()
        
        # Fill NaN
        df = df.fillna(0)
        
        return df
    
    def create_sequences(self, X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Crea secuencias temporales para LSTM
        
        Args:
            X: Features matrix (n_samples, n_features)
            y: Target vector (n_samples,)
        
        Returns:
            X_seq: (n_samples - sequence_length, sequence_length, n_features)
            y_seq: (n_samples - sequence_length,)
        """
        X_seq, y_seq = [], []
        
        for i in range(len(X) - self.sequence_length):
            X_seq.append(X[i:i + self.sequence_length])
            y_seq.append(y[i + self.sequence_length])
        
        return np.array(X_seq), np.array(y_seq)
    
    def train(self, gaps_data: pd.DataFrame, epochs: int = 100, batch_size: int = 32):
        """
        Entrena el modelo LSTM
        
        Args:
            gaps_data: DataFrame con datos históricos de gaps
                       Debe incluir: gap_size, volume, liquidity, timestamp, success
            epochs: Número de épocas de entrenamiento
            batch_size: Tamaño del batch
        """
        logger.info("🚀 Iniciando entrenamiento del modelo LSTM...")
        
        # Preparar features
        df = self.prepare_features(gaps_data)
        
        # Seleccionar columnas de features
        feature_cols = [
            'gap_size_norm', 'volume_log', 'liquidity_log', 'sentiment_score',
            'hour_sin', 'hour_cos', 'day_of_week',
            'gap_size_ma_5', 'gap_size_std_5', 'success_rate_10'
        ]
        
        X = df[feature_cols].values
        y = df['success'].values
        
        # Normalizar features
        X_scaled = self.scaler.fit_transform(X)
        
        # Crear secuencias
        X_seq, y_seq = self.create_sequences(X_scaled, y)
        logger.info(f"📊 Secuencias creadas: {X_seq.shape}")
        
        # Split train/validation
        X_train, X_val, y_train, y_val = train_test_split(
            X_seq, y_seq, test_size=0.2, random_state=42
        )
        
        # Build model
        self.model = self.build_model(input_shape=(self.sequence_length, len(feature_cols)))
        
        # Callbacks
        callbacks = [
            EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True),
            ModelCheckpoint(self.model_path, save_best_only=True, monitor='val_accuracy')
        ]
        
        # Train
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks,
            verbose=1
        )
        
        # Evaluar
        train_loss, train_acc, train_auc = self.model.evaluate(X_train, y_train, verbose=0)
        val_loss, val_acc, val_auc = self.model.evaluate(X_val, y_val, verbose=0)
        
        logger.info(f"✅ Entrenamiento completado")
        logger.info(f"📈 Train Accuracy: {train_acc:.2%} | AUC: {train_auc:.3f}")
        logger.info(f"📊 Val Accuracy: {val_acc:.2%} | AUC: {val_auc:.3f}")
        
        # Guardar scaler
        with open(self.scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)
        
        return history
    
    def predict(self, recent_gaps: List[Dict]) -> Dict:
        """
        Predice probabilidad de éxito de un gap
        
        Args:
            recent_gaps: Lista de últimos N gaps (mínimo sequence_length)
        
        Returns:
            {
                'probability': float,  # Probabilidad de éxito [0,1]
                'confidence': str,     # 'HIGH', 'MEDIUM', 'LOW'
                'recommendation': str, # 'EXECUTE', 'SKIP'
                'sentiment': float     # Score de sentiment
            }
        """
        if self.model is None:
            raise ValueError("Modelo no cargado. Ejecuta train() o load_model() primero.")
        
        if len(recent_gaps) < self.sequence_length:
            logger.warning(f"⚠️ Se necesitan al menos {self.sequence_length} gaps históricos")
            return {
                'probability': 0.0,
                'confidence': 'LOW',
                'recommendation': 'SKIP',
                'sentiment': 0.0
            }
        
        # Preparar features
        df = pd.DataFrame(recent_gaps)
        df = self.prepare_features(df)
        
        feature_cols = [
            'gap_size_norm', 'volume_log', 'liquidity_log', 'sentiment_score',
            'hour_sin', 'hour_cos', 'day_of_week',
            'gap_size_ma_5', 'gap_size_std_5', 'success_rate_10'
        ]
        
        X = df[feature_cols].values[-self.sequence_length:]
        X_scaled = self.scaler.transform(X)
        X_seq = X_scaled.reshape(1, self.sequence_length, -1)
        
        # Predicción
        probability = float(self.model.predict(X_seq, verbose=0)[0][0])
        sentiment = float(df['sentiment_score'].iloc[-1])
        
        # Clasificación de confianza
        if probability >= 0.78:
            confidence = 'HIGH'
            recommendation = 'EXECUTE'
        elif probability >= 0.65:
            confidence = 'MEDIUM'
            recommendation = 'EXECUTE' if sentiment > 0.2 else 'SKIP'
        else:
            confidence = 'LOW'
            recommendation = 'SKIP'
        
        return {
            'probability': probability,
            'confidence': confidence,
            'recommendation': recommendation,
            'sentiment': sentiment
        }
    
    def backtest(self, gaps_data: pd.DataFrame) -> Dict:
        """
        Ejecuta backtest sobre datos históricos
        
        Returns:
            {
                'total_gaps': int,
                'executed_gaps': int,
                'win_rate': float,
                'avg_roi': float,
                'sharpe_ratio': float,
                'max_drawdown': float
            }
        """
        logger.info("🔬 Ejecutando backtest...")
        
        df = self.prepare_features(gaps_data)
        
        predictions = []
        actuals = []
        rois = []
        
        for i in range(self.sequence_length, len(df)):
            recent_gaps = df.iloc[i - self.sequence_length:i].to_dict('records')
            pred = self.predict(recent_gaps)
            
            if pred['recommendation'] == 'EXECUTE':
                predictions.append(pred['probability'])
                actuals.append(df.iloc[i]['success'])
                rois.append(df.iloc[i]['roi'])
        
        # Métricas
        executed_gaps = len(predictions)
        win_rate = np.mean(actuals) if actuals else 0
        avg_roi = np.mean(rois) if rois else 0
        
        # Sharpe Ratio (simplificado)
        if len(rois) > 1:
            sharpe = np.mean(rois) / (np.std(rois) + 1e-6)
        else:
            sharpe = 0
        
        # Max Drawdown
        cumulative = np.cumsum(rois) if rois else [0]
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / (running_max + 1e-6)
        max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0
        
        results = {
            'total_gaps': len(df),
            'executed_gaps': executed_gaps,
            'win_rate': win_rate,
            'avg_roi': avg_roi,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown
        }
        
        logger.info(f"✅ Backtest completado")
        logger.info(f"📊 Win Rate: {win_rate:.2%}")
        logger.info(f"💰 Avg ROI: {avg_roi:.2%}")
        logger.info(f"📈 Sharpe: {sharpe:.2f}")
        logger.info(f"📉 Max DD: {max_drawdown:.2%}")
        
        return results
    
    def save_model(self):
        """Guarda el modelo entrenado"""
        if self.model is not None:
            self.model.save(self.model_path)
            logger.info(f"✅ Modelo guardado en {self.model_path}")
    
    def load_model(self):
        """Carga modelo pre-entrenado"""
        if os.path.exists(self.model_path):
            self.model = load_model(self.model_path)
            logger.info(f"✅ Modelo cargado desde {self.model_path}")
        
        if os.path.exists(self.scaler_path):
            with open(self.scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)
            logger.info(f"✅ Scaler cargado desde {self.scaler_path}")
