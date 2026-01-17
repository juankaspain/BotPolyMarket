"""Sentiment Analyzer - v2.0 ML Gap Predictor

Análisis de sentimiento de noticias y tweets crypto para mejorar predicciones.
Utiliza VADER, TextBlob y feeds RSS para obtener sentimiento en tiempo real.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import asyncio
from dataclasses import dataclass

import feedparser
import requests
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class SentimentData:
    """Datos de sentimiento"""
    source: str  # 'news', 'twitter', 'reddit'
    text: str
    score: float  # -1 a 1
    magnitude: float  # 0 a 1 (intensidad)
    timestamp: datetime
    url: Optional[str] = None
    keywords: List[str] = None


@dataclass
class AggregatedSentiment:
    """Sentimiento agregado de múltiples fuentes"""
    overall_score: float  # -1 a 1
    confidence: float  # 0 a 1
    news_score: float
    social_score: float
    sample_size: int
    dominant_keywords: List[str]
    trend: str  # 'bullish', 'bearish', 'neutral'
    sources: List[SentimentData]


class SentimentAnalyzer:
    """Analizador de sentimiento multi-fuente para predicciones ML"""
    
    # RSS feeds de noticias crypto
    NEWS_FEEDS = [
        'https://cointelegraph.com/rss',
        'https://www.coindesk.com/arc/outboundfeeds/rss/',
        'https://decrypt.co/feed',
        'https://cryptonews.com/news/feed/',
    ]
    
    # Keywords relevantes para prediction markets
    MARKET_KEYWORDS = [
        'prediction', 'polymarket', 'betting', 'odds',
        'election', 'politics', 'sports', 'crypto',
        'bitcoin', 'ethereum', 'defi', 'web3'
    ]
    
    def __init__(self, 
                 twitter_bearer_token: Optional[str] = None,
                 cache_ttl: int = 300):
        """Inicializar analizador
        
        Args:
            twitter_bearer_token: Token de Twitter API (opcional)
            cache_ttl: Tiempo de vida del cache en segundos
        """
        self.vader = SentimentIntensityAnalyzer()
        self.twitter_token = twitter_bearer_token
        self.cache_ttl = cache_ttl
        
        # Cache de sentimientos
        self._sentiment_cache: Dict[str, Tuple[AggregatedSentiment, datetime]] = {}
        self._news_cache: List[Tuple[SentimentData, datetime]] = []
        
        logger.info("Sentiment analyzer initialized")
    
    async def analyze_market_sentiment(self, 
                                      market_name: str,
                                      keywords: Optional[List[str]] = None) -> AggregatedSentiment:
        """Analizar sentimiento para un mercado específico
        
        Args:
            market_name: Nombre del mercado
            keywords: Keywords adicionales para búsqueda
            
        Returns:
            Sentimiento agregado de todas las fuentes
        """
        # Verificar cache
        cache_key = f"{market_name}_{','.join(keywords or [])}"
        if cache_key in self._sentiment_cache:
            cached_sentiment, cache_time = self._sentiment_cache[cache_key]
            if datetime.now() - cache_time < timedelta(seconds=self.cache_ttl):
                logger.debug(f"Using cached sentiment for {market_name}")
                return cached_sentiment
        
        # Extraer keywords del nombre del mercado
        extracted_keywords = self._extract_keywords(market_name)
        if keywords:
            extracted_keywords.extend(keywords)
        
        # Recolectar sentimientos de diferentes fuentes
        all_sentiments: List[SentimentData] = []
        
        # 1. Noticias RSS
        news_sentiments = await self._analyze_news_feeds(extracted_keywords)
        all_sentiments.extend(news_sentiments)
        
        # 2. Twitter (si está disponible)
        if self.twitter_token:
            twitter_sentiments = await self._analyze_twitter(extracted_keywords)
            all_sentiments.extend(twitter_sentiments)
        
        # 3. Reddit (opcional - requiere API)
        # reddit_sentiments = await self._analyze_reddit(extracted_keywords)
        # all_sentiments.extend(reddit_sentiments)
        
        # Agregar sentimientos
        aggregated = self._aggregate_sentiments(all_sentiments, extracted_keywords)
        
        # Guardar en cache
        self._sentiment_cache[cache_key] = (aggregated, datetime.now())
        
        return aggregated
    
    async def _analyze_news_feeds(self, keywords: List[str]) -> List[SentimentData]:
        """Analizar feeds de noticias RSS
        
        Args:
            keywords: Keywords para filtrar noticias relevantes
            
        Returns:
            Lista de sentimientos de noticias
        """
        sentiments = []
        
        for feed_url in self.NEWS_FEEDS:
            try:
                # Parsear feed
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:10]:  # Limitar a 10 últimas noticias
                    # Verificar si la noticia es relevante
                    title = entry.get('title', '')
                    summary = entry.get('summary', '')
                    text = f"{title} {summary}"
                    
                    if not self._is_relevant(text, keywords):
                        continue
                    
                    # Analizar sentimiento
                    score, magnitude = self._analyze_text_sentiment(text)
                    
                    sentiment = SentimentData(
                        source='news',
                        text=title,
                        score=score,
                        magnitude=magnitude,
                        timestamp=self._parse_entry_date(entry),
                        url=entry.get('link'),
                        keywords=keywords
                    )
                    sentiments.append(sentiment)
                    
                    logger.debug(f"News sentiment: {title[:50]}... | Score: {score:.2f}")
                    
            except Exception as e:
                logger.error(f"Error analyzing feed {feed_url}: {e}")
        
        return sentiments
    
    async def _analyze_twitter(self, keywords: List[str]) -> List[SentimentData]:
        """Analizar tweets (requiere Twitter API v2)
        
        Args:
            keywords: Keywords para buscar tweets
            
        Returns:
            Lista de sentimientos de tweets
        """
        if not self.twitter_token:
            return []
        
        sentiments = []
        
        try:
            # Construir query
            query = ' OR '.join(keywords[:5])  # Limitar keywords
            query += ' -is:retweet lang:en'  # Filtrar retweets
            
            # Llamar API de Twitter
            headers = {'Authorization': f'Bearer {self.twitter_token}'}
            params = {
                'query': query,
                'max_results': 100,
                'tweet.fields': 'created_at,public_metrics'
            }
            
            response = requests.get(
                'https://api.twitter.com/2/tweets/search/recent',
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"Twitter API error: {response.status_code}")
                return sentiments
            
            data = response.json()
            tweets = data.get('data', [])
            
            for tweet in tweets:
                text = tweet.get('text', '')
                
                # Limpiar texto
                text = self._clean_tweet_text(text)
                
                # Analizar sentimiento
                score, magnitude = self._analyze_text_sentiment(text)
                
                # Ajustar por engagement (likes, retweets)
                metrics = tweet.get('public_metrics', {})
                engagement_weight = min(1 + (metrics.get('like_count', 0) / 100), 2)
                score *= engagement_weight
                magnitude *= engagement_weight
                
                sentiment = SentimentData(
                    source='twitter',
                    text=text[:100],
                    score=score,
                    magnitude=magnitude,
                    timestamp=datetime.fromisoformat(tweet['created_at'].replace('Z', '+00:00')),
                    keywords=keywords
                )
                sentiments.append(sentiment)
            
            logger.info(f"Analyzed {len(sentiments)} tweets for keywords: {keywords[:3]}")
            
        except Exception as e:
            logger.error(f"Error analyzing Twitter: {e}")
        
        return sentiments
    
    def _analyze_text_sentiment(self, text: str) -> Tuple[float, float]:
        """Analizar sentimiento de un texto usando VADER + TextBlob
        
        Args:
            text: Texto a analizar
            
        Returns:
            (score, magnitude) donde score es -1 a 1 y magnitude es 0 a 1
        """
        # VADER sentiment (mejor para social media)
        vader_scores = self.vader.polarity_scores(text)
        vader_compound = vader_scores['compound']
        
        # TextBlob sentiment (mejor para noticias formales)
        try:
            blob = TextBlob(text)
            textblob_polarity = blob.sentiment.polarity
            textblob_subjectivity = blob.sentiment.subjectivity
        except:
            textblob_polarity = 0
            textblob_subjectivity = 0.5
        
        # Combinar ambos scores (70% VADER, 30% TextBlob)
        combined_score = 0.7 * vader_compound + 0.3 * textblob_polarity
        
        # Magnitude basada en subjetividad y absoluto del score
        magnitude = (abs(combined_score) + textblob_subjectivity) / 2
        
        return combined_score, magnitude
    
    def _aggregate_sentiments(self, 
                             sentiments: List[SentimentData],
                             keywords: List[str]) -> AggregatedSentiment:
        """Agregar sentimientos de múltiples fuentes
        
        Args:
            sentiments: Lista de datos de sentimiento
            keywords: Keywords relevantes
            
        Returns:
            Sentimiento agregado
        """
        if not sentiments:
            # Sentimiento neutral por defecto
            return AggregatedSentiment(
                overall_score=0.0,
                confidence=0.0,
                news_score=0.0,
                social_score=0.0,
                sample_size=0,
                dominant_keywords=keywords[:3],
                trend='neutral',
                sources=[]
            )
        
        # Separar por fuente
        news_sentiments = [s for s in sentiments if s.source == 'news']
        social_sentiments = [s for s in sentiments if s.source in ['twitter', 'reddit']]
        
        # Calcular scores ponderados por magnitude
        def weighted_score(sents: List[SentimentData]) -> float:
            if not sents:
                return 0.0
            total_weight = sum(s.magnitude for s in sents)
            if total_weight == 0:
                return 0.0
            return sum(s.score * s.magnitude for s in sents) / total_weight
        
        news_score = weighted_score(news_sentiments)
        social_score = weighted_score(social_sentiments)
        
        # Score general (70% noticias, 30% social si ambos disponibles)
        if news_sentiments and social_sentiments:
            overall_score = 0.7 * news_score + 0.3 * social_score
        elif news_sentiments:
            overall_score = news_score
        else:
            overall_score = social_score
        
        # Confianza basada en sample size y consistencia
        sample_size = len(sentiments)
        score_variance = sum((s.score - overall_score) ** 2 for s in sentiments) / sample_size
        consistency = 1 / (1 + score_variance)  # Más consistencia = más confianza
        sample_confidence = min(sample_size / 50, 1.0)  # Máx confianza con 50+ samples
        confidence = (consistency + sample_confidence) / 2
        
        # Determinar trend
        if overall_score > 0.2:
            trend = 'bullish'
        elif overall_score < -0.2:
            trend = 'bearish'
        else:
            trend = 'neutral'
        
        # Keywords dominantes (top 3)
        keyword_freq = {}
        for s in sentiments:
            if s.keywords:
                for kw in s.keywords:
                    keyword_freq[kw] = keyword_freq.get(kw, 0) + 1
        dominant_keywords = sorted(keyword_freq.keys(), 
                                  key=lambda k: keyword_freq[k], 
                                  reverse=True)[:3]
        
        return AggregatedSentiment(
            overall_score=overall_score,
            confidence=confidence,
            news_score=news_score,
            social_score=social_score,
            sample_size=sample_size,
            dominant_keywords=dominant_keywords,
            trend=trend,
            sources=sentiments[:10]  # Guardar top 10 para referencia
        )
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extraer keywords relevantes de un texto
        
        Args:
            text: Texto del cual extraer keywords
            
        Returns:
            Lista de keywords
        """
        # Limpiar y tokenizar
        text = text.lower()
        words = re.findall(r'\b[a-z]{3,}\b', text)
        
        # Filtrar palabras comunes
        stopwords = {'the', 'and', 'for', 'with', 'from', 'will', 'this', 'that'}
        keywords = [w for w in words if w not in stopwords]
        
        # Añadir keywords de mercado relevantes
        for market_kw in self.MARKET_KEYWORDS:
            if market_kw in text:
                keywords.append(market_kw)
        
        # Retornar keywords únicos
        return list(set(keywords))[:10]
    
    def _is_relevant(self, text: str, keywords: List[str]) -> bool:
        """Verificar si un texto es relevante según keywords
        
        Args:
            text: Texto a verificar
            keywords: Keywords de relevancia
            
        Returns:
            True si el texto es relevante
        """
        text_lower = text.lower()
        
        # Buscar al menos 1 keyword o 2 palabras relacionadas
        matches = sum(1 for kw in keywords if kw.lower() in text_lower)
        return matches >= 1
    
    @staticmethod
    def _clean_tweet_text(text: str) -> str:
        """Limpiar texto de tweet
        
        Args:
            text: Texto del tweet
            
        Returns:
            Texto limpio
        """
        # Remover URLs
        text = re.sub(r'https?://\S+', '', text)
        # Remover menciones
        text = re.sub(r'@\w+', '', text)
        # Remover hashtags (mantener texto)
        text = re.sub(r'#(\w+)', r'\1', text)
        # Remover caracteres especiales múltiples
        text = re.sub(r'[^\w\s.,!?]', ' ', text)
        # Normalizar espacios
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    @staticmethod
    def _parse_entry_date(entry: dict) -> datetime:
        """Parsear fecha de entrada de feed
        
        Args:
            entry: Entrada de feedparser
            
        Returns:
            Datetime de la entrada
        """
        try:
            if 'published_parsed' in entry:
                from time import mktime
                return datetime.fromtimestamp(mktime(entry.published_parsed))
            elif 'updated_parsed' in entry:
                from time import mktime
                return datetime.fromtimestamp(mktime(entry.updated_parsed))
        except:
            pass
        
        return datetime.now()
    
    def get_sentiment_features(self, market_name: str) -> Dict[str, float]:
        """Obtener features de sentimiento para ML
        
        Args:
            market_name: Nombre del mercado
            
        Returns:
            Diccionario de features para el modelo ML
        """
        # Ejecutar análisis de sentimiento de forma síncrona
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        sentiment = loop.run_until_complete(self.analyze_market_sentiment(market_name))
        loop.close()
        
        return {
            'sentiment_score': sentiment.overall_score,
            'sentiment_confidence': sentiment.confidence,
            'news_sentiment': sentiment.news_score,
            'social_sentiment': sentiment.social_score,
            'sentiment_magnitude': abs(sentiment.overall_score),
            'is_bullish': 1.0 if sentiment.trend == 'bullish' else 0.0,
            'is_bearish': 1.0 if sentiment.trend == 'bearish' else 0.0,
            'sample_size_normalized': min(sentiment.sample_size / 100, 1.0)
        }
