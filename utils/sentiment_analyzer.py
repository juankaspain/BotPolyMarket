#!/usr/bin/env python3
"""
Sentiment Analyzer v2.0
Analiza sentiment de news + crypto tweets para predicción de gaps
"""
import logging
import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import requests
from textblob import TextBlob
import feedparser

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    """
    Analiza sentiment de múltiples fuentes:
    - CryptoCompare News API
    - RSS feeds (CoinDesk, CoinTelegraph)
    - Keywords en market slugs
    
    Output: Score [-1, 1] donde:
    - > 0.5: Muy positivo
    - 0.2 to 0.5: Positivo
    - -0.2 to 0.2: Neutral
    - < -0.2: Negativo
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.cryptocompare_api_key = config.get('cryptocompare_api_key', '')
        self.cache = {}  # Cache de sentiments por market
        self.cache_ttl = 300  # 5 minutos
        
        # RSS feeds de crypto news
        self.news_feeds = [
            'https://cointelegraph.com/rss',
            'https://www.coindesk.com/arc/outboundfeeds/rss/',
            'https://cryptonews.com/news/feed/',
        ]
        
        # Keywords positivas/negativas
        self.positive_keywords = [
            'rally', 'surge', 'bullish', 'adoption', 'breakthrough',
            'partnership', 'upgrade', 'growth', 'record', 'milestone',
            'approve', 'win', 'success', 'innovation', 'launch'
        ]
        
        self.negative_keywords = [
            'crash', 'drop', 'bear', 'hack', 'scam', 'fraud',
            'regulation', 'ban', 'lawsuit', 'warning', 'risk',
            'concern', 'fail', 'collapse', 'crisis', 'decline'
        ]
    
    def get_market_sentiment(self, market_slug: str) -> float:
        """
        Obtiene sentiment score para un market específico
        
        Args:
            market_slug: Identificador del mercado (e.g., "bitcoin-price-2024")
        
        Returns:
            Sentiment score [-1, 1]
        """
        # Check cache
        cache_key = f"{market_slug}:{int(datetime.now().timestamp() / self.cache_ttl)}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Extraer keywords del market slug
        keywords = self._extract_keywords(market_slug)
        
        # Obtener sentiments de múltiples fuentes
        sentiments = []
        
        # 1. Sentiment de keywords en el slug
        slug_sentiment = self._analyze_text(market_slug)
        sentiments.append(slug_sentiment * 0.3)  # Peso 30%
        
        # 2. Sentiment de news
        if keywords:
            news_sentiment = self._get_news_sentiment(keywords)
            sentiments.append(news_sentiment * 0.7)  # Peso 70%
        
        # Calcular score final
        if sentiments:
            final_score = sum(sentiments) / len(sentiments)
        else:
            final_score = 0.0
        
        # Normalizar a [-1, 1]
        final_score = max(-1.0, min(1.0, final_score))
        
        # Cache
        self.cache[cache_key] = final_score
        
        logger.debug(f"Sentiment for '{market_slug}': {final_score:.3f}")
        return final_score
    
    def _extract_keywords(self, market_slug: str) -> List[str]:
        """
        Extrae keywords relevantes del market slug
        
        Ejemplos:
        - "bitcoin-price-2024" -> ["bitcoin"]
        - "trump-election-win" -> ["trump", "election"]
        """
        # Limpiar y tokenizar
        slug = market_slug.lower()
        slug = re.sub(r'[^a-z\s-]', '', slug)
        tokens = slug.split('-')
        
        # Filtrar stopwords comunes
        stopwords = {'will', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for',
                     'by', 'price', 'market', '2024', '2025', '2026'}
        keywords = [t for t in tokens if t not in stopwords and len(t) > 2]
        
        return keywords[:3]  # Max 3 keywords
    
    def _analyze_text(self, text: str) -> float:
        """
        Analiza sentiment de un texto usando TextBlob
        
        Returns:
            Sentiment score [-1, 1]
        """
        try:
            # TextBlob sentiment
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            
            # Keyword boost
            text_lower = text.lower()
            positive_count = sum(1 for kw in self.positive_keywords if kw in text_lower)
            negative_count = sum(1 for kw in self.negative_keywords if kw in text_lower)
            
            keyword_score = (positive_count - negative_count) * 0.1
            
            # Combinar
            final_score = polarity + keyword_score
            return max(-1.0, min(1.0, final_score))
        
        except Exception as e:
            logger.warning(f"Error analyzing text: {e}")
            return 0.0
    
    def _get_news_sentiment(self, keywords: List[str]) -> float:
        """
        Obtiene sentiment de news relacionadas a los keywords
        
        Returns:
            Average sentiment score [-1, 1]
        """
        sentiments = []
        
        # RSS feeds
        for feed_url in self.news_feeds:
            try:
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:10]:  # Top 10 articles
                    title = entry.get('title', '')
                    summary = entry.get('summary', '')
                    text = f"{title} {summary}"
                    
                    # Check si contiene keywords
                    if any(kw in text.lower() for kw in keywords):
                        sentiment = self._analyze_text(text)
                        sentiments.append(sentiment)
            
            except Exception as e:
                logger.debug(f"Error fetching feed {feed_url}: {e}")
                continue
        
        # CryptoCompare API (si está configurado)
        if self.cryptocompare_api_key:
            try:
                cc_sentiment = self._get_cryptocompare_sentiment(keywords)
                if cc_sentiment is not None:
                    sentiments.append(cc_sentiment)
            except Exception as e:
                logger.debug(f"Error with CryptoCompare API: {e}")
        
        # Calcular promedio
        if sentiments:
            return sum(sentiments) / len(sentiments)
        
        return 0.0
    
    def _get_cryptocompare_sentiment(self, keywords: List[str]) -> Optional[float]:
        """
        Obtiene sentiment de CryptoCompare News API
        
        Returns:
            Sentiment score [-1, 1] o None si falla
        """
        if not self.cryptocompare_api_key:
            return None
        
        try:
            url = "https://min-api.cryptocompare.com/data/v2/news/"
            params = {
                'api_key': self.cryptocompare_api_key,
                'lang': 'EN',
                'sortOrder': 'latest'
            }
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get('Data', [])
                
                sentiments = []
                for article in articles[:20]:  # Top 20
                    title = article.get('title', '')
                    body = article.get('body', '')
                    text = f"{title} {body}"
                    
                    # Check keywords
                    if any(kw in text.lower() for kw in keywords):
                        sentiment = self._analyze_text(text)
                        sentiments.append(sentiment)
                
                if sentiments:
                    return sum(sentiments) / len(sentiments)
        
        except Exception as e:
            logger.debug(f"CryptoCompare API error: {e}")
        
        return None
    
    def get_batch_sentiments(self, market_slugs: List[str]) -> Dict[str, float]:
        """
        Obtiene sentiments para múltiples markets en batch
        
        Args:
            market_slugs: Lista de market slugs
        
        Returns:
            Dict {market_slug: sentiment_score}
        """
        results = {}
        
        for slug in market_slugs:
            results[slug] = self.get_market_sentiment(slug)
        
        return results
    
    def clear_cache(self):
        """Limpia el cache de sentiments"""
        self.cache.clear()
        logger.info("✅ Sentiment cache cleared")
