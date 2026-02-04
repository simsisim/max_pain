"""
Quick test of max pain calculator
"""

import sys
sys.path.insert(0, '.')

from src.max_pain_calculator import MaxPainCalculator
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Test with NVDA data
calculator = MaxPainCalculator()

# Use existing NVDA data
nvda_file = 'python/nvda_quotedata.csv'

print("=" * 60)
print("MAX PAIN CALCULATOR - TEST")
print("=" * 60)

try:
    result = calculator.calculate_from_file(nvda_file)

    print(f"\nTicker: {result['ticker']}")
    print(f"Current Price: ${result['current_price']:.2f}")
    print(f"Max Pain Price: ${result['max_pain_price']:.2f}")
    print(f"Percentage Change: {result['pct_change']:.2f}%")
    print(f"Net Call/(Put) Premium: ${result['net_call_put_premium']:,.2f}")
    print(f"Premium Bias: {result['premium_bias'].upper()}")
    print(f"Total Call OI: {result['total_call_oi']:,}")
    print(f"Total Put OI: {result['total_put_oi']:,}")
    print(f"Expiration: {result['expiration_date']}")

    print("\n" + "=" * 60)
    print("Expected values (from PDF report):")
    print("Current Price: $179.92 (close was different than last)")
    print("Max Pain: $172.90")
    print("% Change: -9.08%")
    print("=" * 60)

    # Verify results
    expected_max_pain = 172.90
    tolerance = 5.0  # $5 tolerance

    if abs(result['max_pain_price'] - expected_max_pain) <= tolerance:
        print("\n✓ Test PASSED - Max pain within tolerance")
    else:
        print(f"\n✗ Test FAILED - Max pain {result['max_pain_price']:.2f} differs from expected {expected_max_pain}")

except Exception as e:
    print(f"\n✗ Test FAILED with error: {e}")
    import traceback
    traceback.print_exc()
