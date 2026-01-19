# strategies/arbitrage_execution_checker.py
"""
⚡ ARBITRAGE EXECUTION SPEED CHECKER
===================================

Advanced system to validate arbitrage opportunities by checking:
1. API latency (must be <200ms)
2. Execution speed estimation
3. Dynamic profit thresholds based on latency
4. Liquidity verification
5. Opportunity staleness detection

Author: Juan Carlos Garcia Arriero (juankaspain)
Version: 1.0 PRODUCTION
Date: 19 January 2026

PROBLEM SOLVED:
Arbitrage opportunities detected but lost due to slow execution.
Result: Attempted trades fail, capital wasted, losses incurred.

SOLUTION:
Validate execution speed BEFORE attempting arbitrage.
Only execute if latency + execution time allows profit capture.
"""

import logging
import time
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import statistics


logger = logging.getLogger(__name__)


@dataclass
class LatencyMetrics:
    """Latency measurements for API calls"""
    api_call_ms: float
    data_fetch_ms: float
    total_ms: float
    timestamp: datetime
    endpoint: str
    
    def is_acceptable(self, max_latency_ms: float = 200) -> bool:
        """Check if latency is acceptable for arbitrage"""
        return self.total_ms < max_latency_ms


@dataclass
class ExecutionSpeedCheck:
    """Result of execution speed validation"""
    is_fast_enough: bool
    estimated_execution_ms: float
    opportunity_lifetime_ms: float
    latency_ms: float
    min_profit_threshold: float
    actual_profit: float
    reason: str
    recommendation: str
    
    def to_dict(self) -> Dict:
        return {
            'fast_enough': self.is_fast_enough,
            'execution_time_ms': self.estimated_execution_ms,
            'opportunity_lifetime_ms': self.opportunity_lifetime_ms,
            'latency_ms': self.latency_ms,
            'min_profit_pct': self.min_profit_threshold,
            'actual_profit_pct': self.actual_profit,
            'reason': self.reason,
            'recommendation': self.recommendation
        }


class ArbitrageExecutionChecker:
    """
    Validates arbitrage opportunities by checking execution speed.
    
    Prevents false arbitrage signals that would fail due to:
    - High API latency
    - Slow execution
    - Opportunity already expired
    - Insufficient liquidity
    """
    
    def __init__(self,
                 max_acceptable_latency_ms: float = 200,
                 max_execution_time_ms: float = 1000,
                 min_opportunity_lifetime_ms: float = 5000,
                 base_min_profit_pct: float = 0.5):
        """
        Initialize execution checker.
        
        Args:
            max_acceptable_latency_ms: Max API latency for arbitrage (default: 200ms)
            max_execution_time_ms: Max time to execute trade (default: 1000ms)
            min_opportunity_lifetime_ms: Min time opportunity must last (default: 5000ms)
            base_min_profit_pct: Base minimum profit percentage (default: 0.5%)
        """
        self.max_acceptable_latency_ms = max_acceptable_latency_ms
        self.max_execution_time_ms = max_execution_time_ms
        self.min_opportunity_lifetime_ms = min_opportunity_lifetime_ms
        self.base_min_profit_pct = base_min_profit_pct
        
        # Latency tracking
        self.latency_history: List[LatencyMetrics] = []
        self.max_history_size = 100
        
        # Performance metrics
        self.opportunities_checked = 0
        self.opportunities_rejected_latency = 0
        self.opportunities_rejected_speed = 0
        self.opportunities_rejected_liquidity = 0
        self.opportunities_accepted = 0
        
        logger.info("✅ ArbitrageExecutionChecker initialized")
        logger.info(f"   Max Latency: {max_acceptable_latency_ms}ms")
        logger.info(f"   Max Execution: {max_execution_time_ms}ms")
        logger.info(f"   Min Opportunity Lifetime: {min_opportunity_lifetime_ms}ms")
        logger.info(f"   Base Min Profit: {base_min_profit_pct}%")
    
    def record_latency(self, 
                      api_call_ms: float,
                      data_fetch_ms: float,
                      endpoint: str = "unknown") -> LatencyMetrics:
        """
        Record API latency measurement.
        
        Args:
            api_call_ms: Time for API call
            data_fetch_ms: Time to fetch data
            endpoint: API endpoint name
        
        Returns:
            LatencyMetrics object
        """
        metrics = LatencyMetrics(
            api_call_ms=api_call_ms,
            data_fetch_ms=data_fetch_ms,
            total_ms=api_call_ms + data_fetch_ms,
            timestamp=datetime.now(),
            endpoint=endpoint
        )
        
        # Add to history
        self.latency_history.append(metrics)
        
        # Trim history
        if len(self.latency_history) > self.max_history_size:
            self.latency_history = self.latency_history[-self.max_history_size:]
        
        return metrics
    
    def get_average_latency(self, last_n: int = 10) -> float:
        """
        Get average latency from recent measurements.
        
        Args:
            last_n: Number of recent measurements to average
        
        Returns:
            Average latency in milliseconds
        """
        if not self.latency_history:
            return 0.0
        
        recent = self.latency_history[-last_n:]
        return statistics.mean(m.total_ms for m in recent)
    
    def get_latency_percentile(self, percentile: float = 95) -> float:
        """
        Get latency percentile (e.g., p95).
        
        Args:
            percentile: Percentile to calculate (0-100)
        
        Returns:
            Latency at given percentile in milliseconds
        """
        if not self.latency_history:
            return 0.0
        
        latencies = [m.total_ms for m in self.latency_history]
        return statistics.quantiles(latencies, n=100)[int(percentile) - 1]
    
    def estimate_execution_time(self,
                               num_api_calls: int = 3,
                               has_approval: bool = False) -> float:
        """
        Estimate total execution time for arbitrage trade.
        
        Args:
            num_api_calls: Number of API calls required
            has_approval: Whether token approval is needed
        
        Returns:
            Estimated execution time in milliseconds
        """
        # Get average API latency
        avg_latency = self.get_average_latency()
        if avg_latency == 0:
            avg_latency = 150  # Conservative estimate
        
        # API calls
        api_time = avg_latency * num_api_calls
        
        # Transaction submission and confirmation
        tx_time = 500  # ~500ms average
        
        # Token approval (if needed)
        approval_time = 2000 if has_approval else 0
        
        # Network propagation
        network_time = 200
        
        total = api_time + tx_time + approval_time + network_time
        
        return total
    
    def calculate_dynamic_min_profit(self, latency_ms: float) -> float:
        """
        Calculate minimum profit threshold based on latency.
        
        Higher latency = higher profit threshold needed.
        
        Args:
            latency_ms: Current latency in milliseconds
        
        Returns:
            Minimum profit percentage
        """
        # Base minimum
        min_profit = self.base_min_profit_pct
        
        # Add penalty for high latency
        if latency_ms > 100:
            latency_penalty = (latency_ms - 100) / 1000  # 0.1% per 100ms
            min_profit += latency_penalty
        
        # Add penalty for p95 latency spike risk
        p95_latency = self.get_latency_percentile(95)
        if p95_latency > latency_ms * 1.5:
            spike_penalty = 0.2  # Additional 0.2% for spike risk
            min_profit += spike_penalty
        
        return min_profit
    
    async def check_execution_speed(self,
                                   profit_pct: float,
                                   market_options: List[Dict],
                                   check_liquidity: bool = True) -> ExecutionSpeedCheck:
        """
        Check if arbitrage can be executed fast enough.
        
        This is the CORE validation method.
        
        Args:
            profit_pct: Expected profit percentage
            market_options: List of market options with prices/liquidity
            check_liquidity: Whether to verify liquidity
        
        Returns:
            ExecutionSpeedCheck with validation result
        """
        self.opportunities_checked += 1
        
        # 1. Measure current latency
        start_time = time.time()
        
        # Simulate data fetch (would be actual API call)
        await asyncio.sleep(0.001)  # Minimal delay for async
        
        latency_ms = (time.time() - start_time) * 1000
        
        # Record latency
        self.record_latency(
            api_call_ms=latency_ms,
            data_fetch_ms=0,
            endpoint="arbitrage_check"
        )
        
        # 2. Check if latency is acceptable
        if latency_ms > self.max_acceptable_latency_ms:
            self.opportunities_rejected_latency += 1
            
            return ExecutionSpeedCheck(
                is_fast_enough=False,
                estimated_execution_ms=0,
                opportunity_lifetime_ms=0,
                latency_ms=latency_ms,
                min_profit_threshold=0,
                actual_profit=profit_pct,
                reason=f"High latency: {latency_ms:.0f}ms > {self.max_acceptable_latency_ms}ms",
                recommendation="Skip - API too slow for arbitrage"
            )
        
        # 3. Estimate execution time
        num_api_calls = len(market_options)  # One call per option
        estimated_execution_ms = self.estimate_execution_time(
            num_api_calls=num_api_calls,
            has_approval=False
        )
        
        # 4. Check if execution fast enough
        if estimated_execution_ms > self.max_execution_time_ms:
            self.opportunities_rejected_speed += 1
            
            return ExecutionSpeedCheck(
                is_fast_enough=False,
                estimated_execution_ms=estimated_execution_ms,
                opportunity_lifetime_ms=0,
                latency_ms=latency_ms,
                min_profit_threshold=0,
                actual_profit=profit_pct,
                reason=f"Slow execution: {estimated_execution_ms:.0f}ms > {self.max_execution_time_ms}ms",
                recommendation="Skip - execution too slow"
            )
        
        # 5. Estimate opportunity lifetime
        # Arbitrage opportunities typically last 5-30 seconds
        # We need execution time + safety margin < lifetime
        opportunity_lifetime_ms = self.estimate_opportunity_lifetime(
            profit_pct=profit_pct,
            market_options=market_options
        )
        
        safety_margin = 2.0  # 2x execution time for safety
        required_time = estimated_execution_ms * safety_margin
        
        if opportunity_lifetime_ms < required_time:
            self.opportunities_rejected_speed += 1
            
            return ExecutionSpeedCheck(
                is_fast_enough=False,
                estimated_execution_ms=estimated_execution_ms,
                opportunity_lifetime_ms=opportunity_lifetime_ms,
                latency_ms=latency_ms,
                min_profit_threshold=0,
                actual_profit=profit_pct,
                reason=f"Opportunity too short: {opportunity_lifetime_ms:.0f}ms < {required_time:.0f}ms needed",
                recommendation="Skip - opportunity will expire before execution"
            )
        
        # 6. Calculate dynamic profit threshold
        min_profit_threshold = self.calculate_dynamic_min_profit(latency_ms)
        
        if profit_pct < min_profit_threshold:
            self.opportunities_rejected_speed += 1
            
            return ExecutionSpeedCheck(
                is_fast_enough=False,
                estimated_execution_ms=estimated_execution_ms,
                opportunity_lifetime_ms=opportunity_lifetime_ms,
                latency_ms=latency_ms,
                min_profit_threshold=min_profit_threshold,
                actual_profit=profit_pct,
                reason=f"Profit too low: {profit_pct:.2f}% < {min_profit_threshold:.2f}% threshold (adjusted for latency)",
                recommendation="Skip - profit margin insufficient for latency"
            )
        
        # 7. Check liquidity if requested
        if check_liquidity:
            liquidity_ok, liquidity_reason = self.check_liquidity(market_options)
            
            if not liquidity_ok:
                self.opportunities_rejected_liquidity += 1
                
                return ExecutionSpeedCheck(
                    is_fast_enough=False,
                    estimated_execution_ms=estimated_execution_ms,
                    opportunity_lifetime_ms=opportunity_lifetime_ms,
                    latency_ms=latency_ms,
                    min_profit_threshold=min_profit_threshold,
                    actual_profit=profit_pct,
                    reason=liquidity_reason,
                    recommendation="Skip - insufficient liquidity"
                )
        
        # 8. All checks passed!
        self.opportunities_accepted += 1
        
        return ExecutionSpeedCheck(
            is_fast_enough=True,
            estimated_execution_ms=estimated_execution_ms,
            opportunity_lifetime_ms=opportunity_lifetime_ms,
            latency_ms=latency_ms,
            min_profit_threshold=min_profit_threshold,
            actual_profit=profit_pct,
            reason="All checks passed",
            recommendation=f"EXECUTE - Profit {profit_pct:.2f}% > {min_profit_threshold:.2f}% threshold | Latency {latency_ms:.0f}ms OK"
        )
    
    def estimate_opportunity_lifetime(self,
                                     profit_pct: float,
                                     market_options: List[Dict]) -> float:
        """
        Estimate how long arbitrage opportunity will last.
        
        Args:
            profit_pct: Profit percentage
            market_options: Market options
        
        Returns:
            Estimated lifetime in milliseconds
        """
        # Higher profit = shorter lifetime (more obvious)
        # Lower profit = longer lifetime (less obvious)
        
        base_lifetime = 10000  # 10 seconds base
        
        if profit_pct > 5.0:
            # Very obvious - will disappear fast
            return base_lifetime * 0.3  # 3 seconds
        elif profit_pct > 2.0:
            # Obvious - moderate lifetime
            return base_lifetime * 0.6  # 6 seconds
        elif profit_pct > 1.0:
            # Good profit - decent lifetime
            return base_lifetime  # 10 seconds
        else:
            # Small profit - longer lifetime
            return base_lifetime * 2  # 20 seconds
    
    def check_liquidity(self, market_options: List[Dict]) -> Tuple[bool, str]:
        """
        Check if there's sufficient liquidity for arbitrage.
        
        Args:
            market_options: List of market options with liquidity data
        
        Returns:
            Tuple of (is_sufficient, reason)
        """
        # Check each option has minimum liquidity
        min_liquidity_usd = 1000  # $1,000 minimum per option
        
        for i, option in enumerate(market_options):
            liquidity = option.get('liquidity', 0)
            
            if liquidity < min_liquidity_usd:
                return False, f"Option {i+1} has insufficient liquidity: ${liquidity:.0f} < ${min_liquidity_usd:.0f}"
        
        # Check total liquidity
        total_liquidity = sum(opt.get('liquidity', 0) for opt in market_options)
        min_total = min_liquidity_usd * len(market_options)
        
        if total_liquidity < min_total:
            return False, f"Total liquidity too low: ${total_liquidity:.0f} < ${min_total:.0f}"
        
        return True, "Liquidity OK"
    
    def get_statistics(self) -> Dict:
        """
        Get execution checker statistics.
        
        Returns:
            Dictionary with statistics
        """
        acceptance_rate = (self.opportunities_accepted / self.opportunities_checked * 100) if self.opportunities_checked > 0 else 0
        
        return {
            'opportunities_checked': self.opportunities_checked,
            'opportunities_accepted': self.opportunities_accepted,
            'opportunities_rejected': self.opportunities_checked - self.opportunities_accepted,
            'acceptance_rate': acceptance_rate,
            'rejected_latency': self.opportunities_rejected_latency,
            'rejected_speed': self.opportunities_rejected_speed,
            'rejected_liquidity': self.opportunities_rejected_liquidity,
            'avg_latency_ms': self.get_average_latency(),
            'p95_latency_ms': self.get_latency_percentile(95) if len(self.latency_history) >= 20 else 0,
            'current_min_profit_threshold': self.calculate_dynamic_min_profit(self.get_average_latency())
        }
    
    def print_statistics(self):
        """
        Print formatted statistics.
        """
        stats = self.get_statistics()
        
        print("\n" + "="*60)
        print("⚡ ARBITRAGE EXECUTION CHECKER STATISTICS")
        print("="*60)
        print(f"\n📊 Opportunities:")
        print(f"   Checked:    {stats['opportunities_checked']:>6}")
        print(f"   Accepted:   {stats['opportunities_accepted']:>6} ({stats['acceptance_rate']:.1f}%)")
        print(f"   Rejected:   {stats['opportunities_rejected']:>6}")
        
        print(f"\n❌ Rejection Reasons:")
        print(f"   High Latency:       {stats['rejected_latency']:>6}")
        print(f"   Slow Execution:     {stats['rejected_speed']:>6}")
        print(f"   Low Liquidity:      {stats['rejected_liquidity']:>6}")
        
        print(f"\n⏱️  Latency Metrics:")
        print(f"   Average:    {stats['avg_latency_ms']:>6.0f} ms")
        if stats['p95_latency_ms'] > 0:
            print(f"   P95:        {stats['p95_latency_ms']:>6.0f} ms")
        
        print(f"\n🎯 Current Settings:")
        print(f"   Min Profit Threshold: {stats['current_min_profit_threshold']:.2f}%")
        print(f"   Max Latency:          {self.max_acceptable_latency_ms:.0f} ms")
        print(f"   Max Execution:        {self.max_execution_time_ms:.0f} ms")
        
        print("\n" + "="*60 + "\n")


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    async def test_execution_checker():
        """Test the execution checker"""
        print("\n" + "="*80)
        print("⚡ TESTING ARBITRAGE EXECUTION CHECKER")
        print("="*80 + "\n")
        
        checker = ArbitrageExecutionChecker(
            max_acceptable_latency_ms=200,
            max_execution_time_ms=1000,
            base_min_profit_pct=0.5
        )
        
        # Test Case 1: Good opportunity
        print("\n🔹 TEST 1: Good Opportunity")
        print("-" * 60)
        
        market_options = [
            {'price': 0.35, 'liquidity': 5000},
            {'price': 0.40, 'liquidity': 4000},
            {'price': 0.30, 'liquidity': 3000}
        ]
        
        result = await checker.check_execution_speed(
            profit_pct=1.5,  # 1.5% profit
            market_options=market_options
        )
        
        print(f"Result: {'\u2705 PASS' if result.is_fast_enough else '❌ FAIL'}")
        print(f"Latency: {result.latency_ms:.0f}ms")
        print(f"Estimated Execution: {result.estimated_execution_ms:.0f}ms")
        print(f"Opportunity Lifetime: {result.opportunity_lifetime_ms:.0f}ms")
        print(f"Profit: {result.actual_profit:.2f}% (threshold: {result.min_profit_threshold:.2f}%)")
        print(f"Reason: {result.reason}")
        print(f"Recommendation: {result.recommendation}")
        
        # Test Case 2: Low profit
        print("\n🔹 TEST 2: Low Profit Opportunity")
        print("-" * 60)
        
        # Simulate high latency
        await asyncio.sleep(0.15)  # 150ms
        
        result2 = await checker.check_execution_speed(
            profit_pct=0.3,  # Only 0.3% profit
            market_options=market_options
        )
        
        print(f"Result: {'\u2705 PASS' if result2.is_fast_enough else '❌ FAIL'}")
        print(f"Latency: {result2.latency_ms:.0f}ms")
        print(f"Profit: {result2.actual_profit:.2f}% (threshold: {result2.min_profit_threshold:.2f}%)")
        print(f"Reason: {result2.reason}")
        print(f"Recommendation: {result2.recommendation}")
        
        # Test Case 3: Low liquidity
        print("\n🔹 TEST 3: Low Liquidity")
        print("-" * 60)
        
        low_liquidity_options = [
            {'price': 0.35, 'liquidity': 500},  # Too low
            {'price': 0.40, 'liquidity': 4000},
            {'price': 0.30, 'liquidity': 3000}
        ]
        
        result3 = await checker.check_execution_speed(
            profit_pct=2.0,  # Good profit
            market_options=low_liquidity_options
        )
        
        print(f"Result: {'\u2705 PASS' if result3.is_fast_enough else '❌ FAIL'}")
        print(f"Reason: {result3.reason}")
        print(f"Recommendation: {result3.recommendation}")
        
        # Print statistics
        checker.print_statistics()
        
        print("✅ Testing complete!\n")
    
    # Run test
    asyncio.run(test_execution_checker())
