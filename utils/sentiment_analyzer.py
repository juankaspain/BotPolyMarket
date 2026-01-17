#!/usr/bin/env python3
"""
Sentiment Analyzer v2.0
Analiza sentiment de news, crypto tweets y social media
"""
import logging
import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import os

try:
    import tweepy
    TWEEPY_AVAILABLE = True
except ImportError:
    TWEEPY_AVAILABLE = False

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False

try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

import requests

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    """
    Analizador de sentiment multi-fuente
    
    Sources:
    - Twitter/X API para crypto tweets
    - Reddit API para r/CryptoCurrency, r/PolymarketBets
    - News APIs (NewsAPI, CryptoCompare)
    - VADER para análisis rápido
    - FinBERT para análisis avanzado (opcional)
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.cache = {}  # Cache de sentiments por market
        self.cache_ttl = 300  # 5 minutos
        
        # VADER (lightweight, rápido)
        if VADER_AVAILABLE:
            self.vader = SentimentIntensityAnalyzer()
            logger.info("✅ VADER Sentiment Analyzer loaded")
        else:
            self.vader = None
            logger.warning("⚠️ VADER no disponible. Instalar: pip install vaderSentiment")
        
        # FinBERT (opcional, más preciso pero lento)
        self.finbert = None
        if TRANSFORMERS_AVAILABLE and config.get('use_finbert', False):
            try:
                self.finbert = pipeline("sentiment-analysis", model="ProsusAI/finbert")
                logger.info("✅ FinBERT loaded")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo cargar FinBERT: {e}")
        
        # Twitter API
        self.twitter_client = None
        if TWEEPY_AVAILABLE and config.get('twitter_bearer_token'):
            try:
                self.twitter_client = tweepy.Client(
                    bearer_token=config['twitter_bearer_token']
                )
                logger.info("✅ Twitter API connected")
            except Exception as e:
                logger.warning(f"⚠️ Twitter API error: {e}")
        
        # NewsAPI
        self.news_api_key = config.get('news_api_key')
    
    def get_market_sentiment(self, market_slug: str) -> float:
        """
        Obtiene sentiment agregado de un market
        
        Args:
            market_slug: Slug del mercado (ej: 'trump-win-2024')
        
        Returns:
            Sentiment score [-1.0, 1.0]
            -1.0 = muy negativo
             0.0 = neutral
            +1.0 = muy positivo
        """
        # Check cache
        cache_key = f"sentiment_{market_slug}"
        if cache_key in self.cache:
            cached_time, cached_value = self.cache[cache_key]
            if (datetime.now() - cached_time).seconds < self.cache_ttl:
                return cached_value
        
        # Extraer keywords del market slug
        keywords = self._extract_keywords(market_slug)
        
        sentiments = []
        
        # 1. Twitter sentiment
        if self.twitter_client:
            twitter_sentiment = self._get_twitter_sentiment(keywords)
            if twitter_sentiment is not None:
                sentiments.append(twitter_sentiment)
        
        # 2. News sentiment
        if self.news_api_key:
            news_sentiment = self._get_news_sentiment(keywords)
            if news_sentiment is not None:
                sentiments.append(news_sentiment)
        
        # 3. Reddit sentiment (opcional)
        # reddit_sentiment = self._get_reddit_sentiment(keywords)
        # if reddit_sentiment is not None:
        #     sentiments.append(reddit_sentiment)
        
        # Agregar sentiments (promedio ponderado)
        if sentiments:
            final_sentiment = sum(sentiments) / len(sentiments)
        else:
            final_sentiment = 0.0  # Neutral por defecto
        
        # Cache result
        self.cache[cache_key] = (datetime.now(), final_sentiment)
        
        return final_sentiment
    
    def _extract_keywords(self, market_slug: str) -> List[str]:
        """
        Extrae keywords relevantes del market slug
        
        Ejemplo:
        'trump-win-2024' -> ['trump', 'win', '2024', 'election']
        """
        # Limpiar y separar
        keywords = re.sub(r'[^a-zA-Z0-9\s-]', '', market_slug)
        keywords = keywords.replace('-', ' ').split()
        
        # Agregar contexto según keywords detectadas
        context_map = {
            'trump': ['trump', 'donald', 'maga', 'republican'],
            'bitcoin': ['bitcoin', 'btc', 'crypto'],
            'eth': ['ethereum', 'eth', 'vitalik'],
            'election': ['election', 'vote', 'president'],
        }
        
        expanded = set(keywords)
        for kw in keywords:
            if kw.lower() in context_map:
                expanded.update(context_map[kw.lower()])
        
        return list(expanded)[:5]  # Top 5 keywords
    
    def _get_twitter_sentiment(self, keywords: List[str]) -> Optional[float]:
        """
        Obtiene sentiment de tweets recientes
        
        Returns:
            Sentiment score [-1.0, 1.0] o None si error
        """
        if not self.twitter_client or not self.vader:
            return None
        
        try:
            # Buscar tweets recientes
            query = ' OR '.join(keywords)
            tweets = self.twitter_client.search_recent_tweets(
                query=query,
                max_results=100,
                tweet_fields=['created_at', 'public_metrics']
            )
            
            if not tweets.data:
                return None
            
            sentiments = []
            for tweet in tweets.data:
                # VADER sentiment
                scores = self.vader.polarity_scores(tweet.text)
                sentiments.append(scores['compound'])
            
            return sum(sentiments) / len(sentiments) if sentiments else 0.0
        
        except Exception as e:
            logger.warning(f"⚠️ Twitter sentiment error: {e}")
            return None
    
    def _get_news_sentiment(self, keywords: List[str]) -> Optional[float]:
        """
        Obtiene sentiment de noticias recientes
        
        Returns:
            Sentiment score [-1.0, 1.0] o None si error
        """
        if not self.news_api_key or not self.vader:
            return None
        
        try:
            # NewsAPI endpoint
            url = 'https://newsapi.org/v2/everything'
            params = {
                'q': ' OR '.join(keywords),
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': 50,
                'apiKey': self.news_api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            articles = response.json().get('articles', [])
            
            if not articles:
                return None
            
            sentiments = []
            for article in articles:
                # Analizar título + descripción
                text = f"{article.get('title', '')} {article.get('description', '')}"
                scores = self.vader.polarity_scores(text)
                sentiments.append(scores['compound'])
            
            return sum(sentiments) / len(sentiments) if sentiments else 0.0
        
        except Exception as e:
            logger.warning(f"⚠️ News sentiment error: {e}")
            return None
    
    def analyze_text(self, text: str) -> Dict:
        """
        Analiza sentiment de un texto arbitrario
        
        Returns:
            {
                'score': float,       # Compound score [-1, 1]
                'positive': float,    # Probabilidad positivo
                'negative': float,    # Probabilidad negativo
                'neutral': float,     # Probabilidad neutral
                'label': str          # 'positive', 'negative', 'neutral'
            }
        """
        if self.vader:
            scores = self.vader.polarity_scores(text)
            
            # Clasificación
            if scores['compound'] >= 0.05:
                label = 'positive'
            elif scores['compound'] <= -0.05:
                label = 'negative'
            else:
                label = 'neutral'
            
            return {
                'score': scores['compound'],
                'positive': scores['pos'],
                'negative': scores['neg'],
                'neutral': scores['neu'],
                'label': label
            }
        else:
            return {
                'score': 0.0,
                'positive': 0.33,
                'negative': 0.33,
                'neutral': 0.34,
                'label': 'neutral'
            }
