"""
Debug: Check column structure of CBOE CSV
"""

import pandas as pd

nvda_file = 'python/nvda_quotedata.csv'

# Skip the metadata rows
df = pd.read_csv(nvda_file, skiprows=3)

print("Column names and indices:")
for i, col in enumerate(df.columns):
    print(f"{i:2d}: {col}")

print("\n\nFirst 3 rows of data:")
print(df.head(3))

print("\n\nSample strike data:")
print(df[['Strike', 'Open Interest']].head(10))

# Check if there are duplicate column names
oi_cols = [i for i, col in enumerate(df.columns) if col == 'Open Interest']
print(f"\n\nOpen Interest column indices: {oi_cols}")

if len(oi_cols) >= 2:
    print(f"\nFirst OI column (Calls): column {oi_cols[0]}")
    print(df.iloc[:5, oi_cols[0]])
    print(f"\nSecond OI column (Puts): column {oi_cols[1]}")
    print(df.iloc[:5, oi_cols[1]])
