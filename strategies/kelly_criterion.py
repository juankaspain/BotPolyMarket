"""Kelly Criterion - Enhanced with Auto-Sizing

Integrates:
- Original Kelly Criterion implementation
- Auto position sizing (FASE 1)
- Adaptive Kelly based on performance
- Risk management

Autor: juankaspain
Updated: 18 Enero 2026 - FASE 1 Integration
"""

import logging
from typing import Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class KellyResult:
    """Kelly calculation result"""
    full_kelly: float
    half_kelly: float
    quarter_kelly: float
    recommended: float
    position_size_usd: float
    risk_pct: float


class KellyCriterion:
    """Kelly Criterion for optimal position sizing
    
    Formula: f* = (p * b - q) / b
    Where:
        f* = Kelly fraction
        p = win probability
        q = loss probability (1-p)
        b = win/loss ratio
    """
    
    def __init__(self, 
                 bankroll: float,
                 kelly_fraction: float = 0.5,
                 max_position_pct: float = 0.10,
                 min_position_usd: float = 10.0,
                 max_position_usd: float = 1000.0):
        """
        Args:
            bankroll: Total capital
            kelly_fraction: Fraction of Kelly to use (0.5 = Half Kelly)
            max_position_pct: Max % of bankroll per position
            min_position_usd: Minimum position size
            max_position_usd: Maximum position size
        """
        self.bankroll = bankroll
        self.kelly_fraction = kelly_fraction
        self.max_position_pct = max_position_pct
        self.min_position_usd = min_position_usd
        self.max_position_usd = max_position_usd
        
        # Performance tracking
        self.trades = []
        self.win_streak = 0
        self.loss_streak = 0
        
        logger.info(f"Kelly Criterion initialized: ${bankroll:,.2f} bankroll, {kelly_fraction} fraction")
    
    def calculate_fraction(self, 
                          win_probability: float,
                          win_return: float,
                          loss_return: float = 1.0) -> float:
        """Calculate Kelly fraction
        
        Args:
            win_probability: Probability of winning (0-1)
            win_return: Return multiplier if win
            loss_return: Loss multiplier if lose (default 1.0)
            
        Returns:
            Kelly fraction (0-1)
        """
        p = win_probability
        q = 1 - p
        b = win_return / loss_return
        
        kelly = (p * b - q) / b
        
        return max(0, kelly)
    
    def calculate_position_size(self,
                               win_probability: float,
                               risk_reward_ratio: float,
                               confidence: float = 1.0) -> KellyResult:
        """Calculate optimal position size
        
        Args:
            win_probability: Expected win rate (0-1 or 0-100)
            risk_reward_ratio: R:R ratio
            confidence: Confidence multiplier (0-1)
            
        Returns:
            KellyResult object
        """
        # Normalize
        if win_probability > 1:
            win_probability = win_probability / 100
        if confidence > 1:
            confidence = confidence / 100
        
        # Calculate Kelly
        full_kelly = self.calculate_fraction(
            win_probability=win_probability,
            win_return=risk_reward_ratio
        )
        
        half_kelly = full_kelly * 0.5
        quarter_kelly = full_kelly * 0.25
        
        # Recommended
        recommended = full_kelly * self.kelly_fraction * confidence
        recommended = min(recommended, self.max_position_pct)
        
        # Position size
        position_size = recommended * self.bankroll
        position_size = max(self.min_position_usd, position_size)
        position_size = min(self.max_position_usd, position_size)
        
        risk_pct = (position_size / self.bankroll) * 100
        
        return KellyResult(
            full_kelly=full_kelly,
            half_kelly=half_kelly,
            quarter_kelly=quarter_kelly,
            recommended=recommended,
            position_size_usd=position_size,
            risk_pct=risk_pct
        )
    
    def should_take_trade(self, 
                         win_rate: float,
                         risk_reward: float,
                         confidence: float = 70) -> Tuple[bool, str]:
        """Determine if trade should be taken
        
        Returns:
            (should_take, reason)
        """
        result = self.calculate_position_size(win_rate, risk_reward, confidence)
        
        if result.full_kelly <= 0:
            return False, "Negative expectancy"
        
        if result.position_size_usd < self.min_position_usd:
            return False, f"Position too small (${result.position_size_usd:.2f})"
        
        if confidence < 60:
            return False, f"Confidence too low ({confidence}%)"
        
        return True, f"Approved: ${result.position_size_usd:.2f} ({result.risk_pct:.2f}% risk)"
    
    def record_trade(self, won: bool, profit_loss: float):
        """Record trade result for adaptive Kelly"""
        self.trades.append({
            'won': won,
            'pnl': profit_loss,
            'timestamp': datetime.now().timestamp()
        })
        
        if won:
            self.win_streak += 1
            self.loss_streak = 0
        else:
            self.loss_streak += 1
            self.win_streak = 0
        
        self.update_bankroll(self.bankroll + profit_loss)
        self._adapt_kelly_fraction()
    
    def _adapt_kelly_fraction(self):
        """Adapt Kelly fraction based on recent performance"""
        if len(self.trades) < 10:
            return
        
        recent = self.trades[-20:]
        recent_wr = sum(1 for t in recent if t['won']) / len(recent)
        
        if recent_wr > 0.70:
            self.kelly_fraction = min(0.6, self.kelly_fraction * 1.1)
            logger.info(f"⬆️ Kelly fraction increased to {self.kelly_fraction:.2f}")
        elif recent_wr < 0.50:
            self.kelly_fraction = max(0.25, self.kelly_fraction * 0.9)
            logger.warning(f"⬇️ Kelly fraction decreased to {self.kelly_fraction:.2f}")
    
    def update_bankroll(self, new_bankroll: float):
        """Update bankroll after profit/loss"""
        old = self.bankroll
        self.bankroll = new_bankroll
        change = ((new_bankroll - old) / old) * 100
        logger.info(f"Bankroll: ${old:,.2f} → ${new_bankroll:,.2f} ({change:+.2f}%)")
    
    def get_statistics(self) -> dict:
        """Get performance statistics"""
        if not self.trades:
            return {}
        
        total = len(self.trades)
        wins = sum(1 for t in self.trades if t['won'])
        losses = total - wins
        
        total_profit = sum(t['pnl'] for t in self.trades if t['pnl'] > 0)
        total_loss = abs(sum(t['pnl'] for t in self.trades if t['pnl'] < 0))
        net = sum(t['pnl'] for t in self.trades)
        
        return {
            'total_trades': total,
            'wins': wins,
            'losses': losses,
            'win_rate': wins / total,
            'total_profit': total_profit,
            'total_loss': total_loss,
            'net_profit': net,
            'profit_factor': total_profit / total_loss if total_loss > 0 else 0,
            'avg_win': total_profit / wins if wins > 0 else 0,
            'avg_loss': total_loss / losses if losses > 0 else 0,
            'streak': self.win_streak if self.win_streak > 0 else -self.loss_streak,
            'kelly_fraction': self.kelly_fraction
        }
