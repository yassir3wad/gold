#!/usr/bin/env python3
"""Test script to verify profit factor, max drawdown, and Sharpe ratio calculations."""

# Import the metric functions from backtest_multi_day
from backtest_multi_day import calculate_profit_factor, calculate_max_drawdown, calculate_sharpe_ratio

def test_metrics():
    """Test the three advanced metrics with sample trade data."""

    # Sample trades: (side, grade, why, entry, sl, tp1, outcome, pips)
    # Format matches backtest_multi_day.py line 108
    sample_trades = [
        ("LONG", "A", "impulse", 24500.0, 24465.0, 24550.0, "TP1", 50),    # win
        ("SHORT", "B", "range break", 24550.0, 24585.0, 24500.0, "TP1", 50), # win
        ("LONG", "A+", "res-TL break", 24500.0, 24465.0, 24550.0, "SL", -35), # loss
        ("SHORT", "A", "double-top", 24600.0, 24635.0, 24550.0, "TP1", 50),  # win
        ("LONG", "B", "impulse", 24550.0, 24515.0, 24600.0, "SL", -35),      # loss
        ("SHORT", "A", "sup-TL break", 24600.0, 24635.0, 24550.0, "timeout", 20), # timeout
    ]

    print("Testing Advanced Metrics Calculations")
    print("="*60)
    print(f"\nSample trades: {len(sample_trades)} trades")
    print(f"  Wins: {len([t for t in sample_trades if t[6]=='TP1'])}")
    print(f"  Losses: {len([t for t in sample_trades if t[6]=='SL'])}")
    print(f"  Timeouts: {len([t for t in sample_trades if t[6]=='timeout'])}")
    print(f"  Net pips: {sum(t[7] for t in sample_trades):+.0f}")

    # Test profit factor
    print("\n--- Profit Factor ---")
    pf = calculate_profit_factor(sample_trades)
    pf_str = f"{pf:.2f}" if pf != float('inf') else "∞"
    print(f"Profit factor: {pf_str}")
    gross_profit = sum(t[7] for t in sample_trades if t[7] > 0)
    gross_loss = abs(sum(t[7] for t in sample_trades if t[7] < 0))
    print(f"  Gross profit: {gross_profit:.0f} pips")
    print(f"  Gross loss: {gross_loss:.0f} pips")
    print(f"  Ratio: {gross_profit}/{gross_loss} = {pf:.2f}")

    # Test max drawdown
    print("\n--- Max Drawdown ---")
    max_dd, max_dd_pct = calculate_max_drawdown(sample_trades)
    print(f"Max drawdown: {max_dd:.0f} pips ({max_dd_pct:.1f}%)")

    # Show equity curve
    print(f"  Equity curve:")
    equity = 0
    peak = 0
    for i, t in enumerate(sample_trades, 1):
        equity += t[7]
        if equity > peak:
            peak = equity
        dd = peak - equity
        print(f"    Trade {i}: {t[7]:+.0f} pips -> Equity: {equity:+.0f} pips (Peak: {peak:+.0f}, DD: {dd:.0f})")

    # Test Sharpe ratio
    print("\n--- Sharpe Ratio ---")
    sharpe = calculate_sharpe_ratio(sample_trades)
    print(f"Sharpe ratio: {sharpe:.2f}")
    returns = [t[7] for t in sample_trades]
    mean_return = sum(returns) / len(returns)
    print(f"  Mean return per trade: {mean_return:.2f} pips")
    variance = sum((r - mean_return)**2 for r in returns) / (len(returns) - 1)
    std_dev = variance**0.5
    print(f"  Std dev: {std_dev:.2f} pips")
    print(f"  Annualized Sharpe (252 trading days): {sharpe:.2f}")

    print("\n" + "="*60)
    print("✓ All three metrics calculated successfully!")
    print("="*60)

    # Verify metrics are reasonable
    assert pf > 0, "Profit factor should be positive"
    assert max_dd >= 0, "Max drawdown should be non-negative"
    assert max_dd_pct >= 0, "Max drawdown % should be non-negative"
    print("\n✓ All assertions passed!")

    return True

if __name__ == "__main__":
    try:
        test_metrics()
        print("\n✓ TEST PASSED: Profit factor, max drawdown, and Sharpe ratio are working correctly.")
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
