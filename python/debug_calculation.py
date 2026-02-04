"""
Debug: Detailed max pain calculation
"""

import sys
sys.path.insert(0, '.')

from src.max_pain_calculator import MaxPainCalculator
import pandas as pd

calculator = MaxPainCalculator()

# Load data
nvda_file = 'python/nvda_quotedata.csv'
df, current_price, expiration_date, ticker = calculator.load_cboe_csv(nvda_file)
option_data = calculator.parse_option_chain(df)

print(f"Current Price: ${current_price:.2f}")
print(f"Number of strikes: {len(option_data)}")
print(f"\nSample of option data:")
print(option_data.head(20))

# Calculate pain at a few key strikes
test_strikes = [140, 144, 170, 172.90, 175, 180]

print("\n" + "=" * 80)
print("Pain calculation at key strikes:")
print("=" * 80)

for test_price in test_strikes:
    total, call_p, put_p = calculator.calculate_pain_at_price(test_price, option_data)
    print(f"\nPrice: ${test_price:7.2f}")
    print(f"  Call payout: ${call_p:15,.0f}")
    print(f"  Put payout:  ${put_p:15,.0f}")
    print(f"  Total:       ${total:15,.0f}")

# Find the actual min
print("\n" + "=" * 80)
print("Finding minimum payout strike:")
print("=" * 80)

pain_at_each_strike = []
for strike in option_data['Strike'].values:
    total, call_p, put_p = calculator.calculate_pain_at_price(strike, option_data)
    pain_at_each_strike.append({
        'strike': strike,
        'total_payout': total,
        'call_payout': call_p,
        'put_payout': put_p
    })

pain_df = pd.DataFrame(pain_at_each_strike)
pain_df = pain_df.sort_values('total_payout')

print("\nTop 10 strikes with LOWEST total payout:")
print(pain_df.head(10).to_string(index=False))

print("\n Strikes around $170-$180:")
nearby = pain_df[(pain_df['strike'] >= 170) & (pain_df['strike'] <= 180)]
print(nearby.sort_values('strike').to_string(index=False))
