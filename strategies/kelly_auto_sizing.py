"""Kelly Criterion Auto-Sizing

Implementación automática de Kelly Criterion para:
- Position sizing óptimo
- Risk management dinámico
- Bankroll protection

Autor: juankaspain
"""

import logging
from typing import Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class KellyResult:
    """Resultado de cálculo Kelly"""
    full_kelly: float          # Kelly completo (arriesgado)
    half_kelly: float          # 50% Kelly (recomendado)
    quarter_kelly: float       # 25% Kelly (conservador)
    recommended: float         # Tamaño recomendado
    position_size_usd: float   # Tamaño en USD
    risk_pct: float            # % del bankroll en riesgo


class KellyAutoSizing:
    """Kelly Criterion con auto-sizing inteligente"""
    
    def __init__(self, 
                 bankroll: float,
                 kelly_fraction: float = 0.5,  # Half Kelly por defecto
                 max_position_pct: float = 0.10,  # Máx 10% del bankroll
                 min_position_usd: float = 10.0,   # Mínimo $10
                 max_position_usd: float = 1000.0):  # Máximo $1000
        """
        Args:
            bankroll: Capital total disponible
            kelly_fraction: Fracción de Kelly a usar (0.5 = Half Kelly)
            max_position_pct: Máximo % del bankroll por posición
            min_position_usd: Tamaño mínimo en USD
            max_position_usd: Tamaño máximo en USD
        """
        self.bankroll = bankroll
        self.kelly_fraction = kelly_fraction
        self.max_position_pct = max_position_pct
        self.min_position_usd = min_position_usd
        self.max_position_usd = max_position_usd
        
        logger.info(f"KellyAutoSizing initialized: ${bankroll:,.2f} bankroll")
    
    def calculate_kelly(self, 
                       win_probability: float,
                       win_return: float,
                       loss_return: float = 1.0) -> float:
        """Calculate Kelly fraction
        
        Formula: f* = (p * b - q) / b
        
        Where:
            f* = Kelly fraction
            p = win probability (0-1)
            q = loss probability (1-p)
            b = win/loss ratio (profit per $1 risked)
        
        Args:
            win_probability: Probability of winning (0-1)
            win_return: Return multiplier if win (e.g., 2.0 = 2x)
            loss_return: Loss multiplier if lose (default 1.0 = 100% loss)
            
        Returns:
            Kelly fraction (0-1)
        """
        p = win_probability
        q = 1 - p
        b = win_return / loss_return
        
        # Kelly formula
        kelly = (p * b - q) / b
        
        # Never negative (would mean -EV trade)
        return max(0, kelly)
    
    def calculate_position_size(self,
                               win_probability: float,
                               risk_reward_ratio: float,
                               confidence_adjustment: float = 1.0) -> KellyResult:
        """Calculate optimal position size using Kelly
        
        Args:
            win_probability: Expected win rate (0-1 or 0-100)
            risk_reward_ratio: R:R ratio (e.g., 3.0 = 1:3 R:R)
            confidence_adjustment: Multiplier para ajustar por confianza (0-1)
            
        Returns:
            KellyResult with recommended position size
        """
        # Normalize win probability
        if win_probability > 1:
            win_probability = win_probability / 100
        
        # Calculate Kelly
        full_kelly = self.calculate_kelly(
            win_probability=win_probability,
            win_return=risk_reward_ratio
        )
        
        # Apply Kelly fractions
        half_kelly = full_kelly * 0.5
        quarter_kelly = full_kelly * 0.25
        
        # Recommended = Kelly fraction * confidence adjustment
        recommended_fraction = full_kelly * self.kelly_fraction * confidence_adjustment
        
        # Apply limits
        recommended_fraction = min(recommended_fraction, self.max_position_pct)
        
        # Calculate position size in USD
        position_size = recommended_fraction * self.bankroll
        
        # Apply min/max limits
        position_size = max(self.min_position_usd, position_size)
        position_size = min(self.max_position_usd, position_size)
        
        # Final risk percentage
        risk_pct = (position_size / self.bankroll) * 100
        
        return KellyResult(
            full_kelly=full_kelly,
            half_kelly=half_kelly,
            quarter_kelly=quarter_kelly,
            recommended=recommended_fraction,
            position_size_usd=position_size,
            risk_pct=risk_pct
        )
    
    def calculate_from_signal(self, signal) -> KellyResult:
        """Calculate position size from a GapSignal object
        
        Args:
            signal: GapSignal object with expected_win_rate, risk_reward_ratio, confidence
            
        Returns:
            KellyResult
        """
        # Extract parameters from signal
        win_rate = signal.expected_win_rate / 100  # Convert % to decimal
        rr_ratio = signal.risk_reward_ratio
        confidence = signal.confidence / 100  # Use confidence as adjustment
        
        return self.calculate_position_size(
            win_probability=win_rate,
            risk_reward_ratio=rr_ratio,
            confidence_adjustment=confidence
        )
    
    def update_bankroll(self, new_bankroll: float):
        """Update bankroll after profit/loss"""
        old_bankroll = self.bankroll
        self.bankroll = new_bankroll
        
        change = ((new_bankroll - old_bankroll) / old_bankroll) * 100
        logger.info(f"Bankroll updated: ${old_bankroll:,.2f} → ${new_bankroll:,.2f} ({change:+.2f}%)")
    
    def get_max_concurrent_positions(self, avg_position_pct: float = 0.05) -> int:
        """Calculate max concurrent positions
        
        Args:
            avg_position_pct: Average position size as % of bankroll
            
        Returns:
            Max number of concurrent positions
        """
        # Reserve 20% of bankroll as buffer
        usable_pct = 0.80
        
        max_positions = int((usable_pct / avg_position_pct))
        
        # Reasonable limits
        max_positions = max(3, min(max_positions, 20))
        
        return max_positions
    
    def should_take_trade(self, signal) -> Tuple[bool, str]:
        """Determine if trade should be taken based on Kelly
        
        Returns:
            (should_take: bool, reason: str)
        """
        kelly_result = self.calculate_from_signal(signal)
        
        # Negative Kelly = negative expectancy
        if kelly_result.full_kelly <= 0:
            return False, f"Negative expectancy (Kelly={kelly_result.full_kelly:.3f})"
        
        # Position too small (not worth the fees)
        if kelly_result.position_size_usd < self.min_position_usd:
            return False, f"Position too small (${kelly_result.position_size_usd:.2f} < ${self.min_position_usd})"
        
        # Low confidence
        if signal.confidence < 60:
            return False, f"Confidence too low ({signal.confidence}% < 60%)"
        
        # All checks passed
        return True, f"Kelly approved: ${kelly_result.position_size_usd:.2f} ({kelly_result.risk_pct:.2f}% risk)"


class AdaptiveKelly(KellyAutoSizing):
    """Kelly adaptativo que ajusta parámetros según rendimiento"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Track performance
        self.trades = []
        self.win_streak = 0
        self.loss_streak = 0
        
    def record_trade(self, won: bool, profit_loss: float):
        """Record trade result
        
        Args:
            won: True if trade won
            profit_loss: Profit/loss in USD
        """
        self.trades.append({
            'won': won,
            'pnl': profit_loss,
            'timestamp': datetime.now().timestamp()
        })
        
        # Update streaks
        if won:
            self.win_streak += 1
            self.loss_streak = 0
        else:
            self.loss_streak += 1
            self.win_streak = 0
        
        # Update bankroll
        self.update_bankroll(self.bankroll + profit_loss)
        
        # Adaptive adjustment
        self._adjust_kelly_fraction()
    
    def _adjust_kelly_fraction(self):
        """Adjust Kelly fraction based on recent performance"""
        if len(self.trades) < 10:
            return  # Need minimum sample size
        
        # Recent performance (last 20 trades)
        recent = self.trades[-20:]
        recent_win_rate = sum(1 for t in recent if t['won']) / len(recent)
        
        # Adjust Kelly fraction
        if recent_win_rate > 0.70:
            # Performing well - can be more aggressive
            self.kelly_fraction = min(0.6, self.kelly_fraction * 1.1)
            logger.info(f"⬆️ Increasing Kelly fraction to {self.kelly_fraction:.2f} (win rate {recent_win_rate:.1%})")
        
        elif recent_win_rate < 0.50:
            # Underperforming - be more conservative
            self.kelly_fraction = max(0.25, self.kelly_fraction * 0.9)
            logger.warning(f"⬇️ Decreasing Kelly fraction to {self.kelly_fraction:.2f} (win rate {recent_win_rate:.1%})")
        
        # Stop trading if too many consecutive losses
        if self.loss_streak >= 5:
            logger.error(f"🛑 5 consecutive losses - consider pausing trading")
    
    def get_statistics(self) -> dict:
        """Get performance statistics"""
        if not self.trades:
            return {}
        
        total_trades = len(self.trades)
        wins = sum(1 for t in self.trades if t['won'])
        losses = total_trades - wins
        
        total_profit = sum(t['pnl'] for t in self.trades if t['pnl'] > 0)
        total_loss = abs(sum(t['pnl'] for t in self.trades if t['pnl'] < 0))
        net_profit = sum(t['pnl'] for t in self.trades)
        
        return {
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses,
            'win_rate': wins / total_trades if total_trades > 0 else 0,
            'total_profit': total_profit,
            'total_loss': total_loss,
            'net_profit': net_profit,
            'profit_factor': total_profit / total_loss if total_loss > 0 else 0,
            'avg_win': total_profit / wins if wins > 0 else 0,
            'avg_loss': total_loss / losses if losses > 0 else 0,
            'current_streak': self.win_streak if self.win_streak > 0 else -self.loss_streak,
            'kelly_fraction': self.kelly_fraction
        }


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    from datetime import datetime
    
    # Initialize Kelly
    kelly = AdaptiveKelly(
        bankroll=10000,
        kelly_fraction=0.5,  # Half Kelly
        max_position_pct=0.10
    )
    
    # Example signal
    from dataclasses import dataclass
    
    @dataclass
    class MockSignal:
        expected_win_rate: float = 65.0  # 65%
        risk_reward_ratio: float = 3.0   # 1:3 R:R
        confidence: float = 70.0         # 70% confidence
    
    signal = MockSignal()
    
    # Calculate position size
    result = kelly.calculate_from_signal(signal)
    
    print("\n📊 Kelly Auto-Sizing Results:")
    print("=" * 50)
    print(f"Full Kelly:      {result.full_kelly:.2%}")
    print(f"Half Kelly:      {result.half_kelly:.2%}")
    print(f"Quarter Kelly:   {result.quarter_kelly:.2%}")
    print(f"Recommended:     {result.recommended:.2%}")
    print(f"Position Size:   ${result.position_size_usd:,.2f}")
    print(f"Risk %:          {result.risk_pct:.2f}%")
    
    # Should take trade?
    should_take, reason = kelly.should_take_trade(signal)
    print(f"\nTake Trade:      {should_take}")
    print(f"Reason:          {reason}")
    
    # Simulate trades
    print("\n🎲 Simulating 10 trades...")
    for i in range(10):
        won = i % 3 != 0  # 66% win rate
        pnl = 30 if won else -10
        kelly.record_trade(won, pnl)
    
    # Statistics
    stats = kelly.get_statistics()
    print("\n📊 Performance Statistics:")
    print("=" * 50)
    print(f"Total Trades:    {stats['total_trades']}")
    print(f"Win Rate:        {stats['win_rate']:.1%}")
    print(f"Net Profit:      ${stats['net_profit']:,.2f}")
    print(f"Profit Factor:   {stats['profit_factor']:.2f}")
    print(f"Current Streak:  {stats['current_streak']:+d}")
    print(f"Kelly Fraction:  {stats['kelly_fraction']:.2f}")
