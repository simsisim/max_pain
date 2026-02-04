"""
Max Pain Calculator - Core calculation engine

Calculates the "max pain" strike price where market makers would pay out
the least amount of premium at options expiration.
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime


class MaxPainCalculator:
    """
    Max Pain Calculator

    Methodology:
    1. For each potential expiration price point:
       - Calculate call payout: Σ(max(0, price - strike) × call_OI × 100)
       - Calculate put payout: Σ(max(0, strike - price) × put_OI × 100)
    2. Max pain = price point with MINIMUM total payout
    3. Net premium = difference between call and put open interest value
    """

    def __init__(self):
        self.logger = logging.getLogger('max_pain.calculator')

    def load_cboe_csv(self, filepath):
        """
        Load CBOE option chain data from CSV file

        Args:
            filepath: Path to CBOE CSV file

        Returns:
            tuple: (option_chain_df, current_price, expiration_date, ticker)
        """
        self.logger.info(f"Loading CBOE data from {filepath}")

        try:
            # Read the first few lines to extract metadata
            with open(filepath, 'r') as f:
                lines = f.readlines()

            # File format:
            # Line 0: Empty
            # Line 1: Company name, Last price, Change
            # Line 2: Date info
            # Line 3: Column headers
            # Line 4+: Option data

            # Find the line with company info (look for "Last:")
            header_line = None
            skip_rows = 0
            for i, line in enumerate(lines):
                if 'Last:' in line:
                    header_line = line.strip()
                    skip_rows = i + 2  # Skip metadata lines plus header
                    break

            if not header_line:
                raise ValueError("Could not find price information in CSV")

            # Parse company name and price
            parts = header_line.split(',')
            company_name = parts[0] if parts else "Unknown"

            # Extract ticker - handle empty or short company names
            ticker_parts = company_name.strip().split()
            ticker = ticker_parts[0].upper() if ticker_parts else "UNKNOWN"

            # Extract current price
            last_price_str = parts[1].replace('Last:', '').strip() if len(parts) > 1 else "0"
            current_price = float(last_price_str)

            self.logger.debug(f"Parsed ticker: {ticker}, price: ${current_price:.2f}")

            # Read the actual option chain data
            df = pd.read_csv(filepath, skiprows=skip_rows)

            self.logger.debug(f"Loaded {len(df)} option rows")
            self.logger.debug(f"Columns: {df.columns.tolist()}")

            # Extract expiration date from first row
            expiration_date = df['Expiration Date'].iloc[0] if 'Expiration Date' in df.columns else None

            return df, current_price, expiration_date, ticker

        except Exception as e:
            self.logger.error(f"Error loading CBOE CSV: {e}")
            raise

    def parse_option_chain(self, df):
        """
        Parse option chain DataFrame and extract relevant data

        Args:
            df: Raw option chain DataFrame

        Returns:
            DataFrame with columns: Strike, Call_OI, Put_OI
        """
        self.logger.debug("Parsing option chain data")

        # Extract relevant columns
        # Based on CBOE format: Strike is column 11, Call OI is column 10, Put OI is column 21
        # When pandas reads duplicate column names, it renames them with .1, .2, etc.
        try:
            strikes = df['Strike'].values

            # Call OI is the first "Open Interest" column (column 10)
            call_oi = df['Open Interest'].values

            # Put OI is the second "Open Interest" column, renamed by pandas to "Open Interest.1"
            if 'Open Interest.1' in df.columns:
                put_oi = df['Open Interest.1'].values
            else:
                # Fallback: find all OI columns
                oi_cols = [col for col in df.columns if 'Open Interest' in col]
                if len(oi_cols) >= 2:
                    put_oi = df[oi_cols[1]].values
                else:
                    raise ValueError("Could not find Put Open Interest column")

            # Create clean DataFrame
            option_data = pd.DataFrame({
                'Strike': strikes,
                'Call_OI': call_oi,
                'Put_OI': put_oi
            })

            # Clean data: remove NaN and convert to numeric
            option_data['Strike'] = pd.to_numeric(option_data['Strike'], errors='coerce')
            option_data['Call_OI'] = pd.to_numeric(option_data['Call_OI'], errors='coerce').fillna(0)
            option_data['Put_OI'] = pd.to_numeric(option_data['Put_OI'], errors='coerce').fillna(0)

            # Remove rows with invalid strikes
            option_data = option_data.dropna(subset=['Strike'])
            option_data = option_data[option_data['Strike'] > 0]

            self.logger.info(f"Parsed {len(option_data)} valid option strikes")
            self.logger.debug(f"Strike range: ${option_data['Strike'].min():.2f} - ${option_data['Strike'].max():.2f}")
            self.logger.debug(f"Total Call OI: {option_data['Call_OI'].sum():,.0f}")
            self.logger.debug(f"Total Put OI: {option_data['Put_OI'].sum():,.0f}")

            return option_data

        except Exception as e:
            self.logger.error(f"Error parsing option chain: {e}")
            raise

    def calculate_pain_at_price(self, price, option_data):
        """
        Calculate total payout at a given price point

        Args:
            price: Price point to evaluate
            option_data: DataFrame with Strike, Call_OI, Put_OI

        Returns:
            tuple: (total_payout, call_payout, put_payout)
        """
        # Call payout: sum of (price - strike) * call_OI for ITM calls
        # ITM calls: strike < price
        call_payout = 0
        for _, row in option_data.iterrows():
            strike = row['Strike']
            if price > strike:
                call_payout += (price - strike) * row['Call_OI'] * 100

        # Put payout: sum of (strike - price) * put_OI for ITM puts
        # ITM puts: strike > price
        put_payout = 0
        for _, row in option_data.iterrows():
            strike = row['Strike']
            if price < strike:
                put_payout += (strike - price) * row['Put_OI'] * 100

        total_payout = call_payout + put_payout

        return total_payout, call_payout, put_payout

    def calculate_max_pain(self, option_data, current_price):
        """
        Calculate max pain price

        Args:
            option_data: DataFrame with Strike, Call_OI, Put_OI
            current_price: Current stock price

        Returns:
            dict with calculation results
        """
        self.logger.info("Calculating max pain price")

        # Get range of strikes to evaluate
        min_strike = option_data['Strike'].min()
        max_strike = option_data['Strike'].max()

        self.logger.debug(f"Evaluating strikes from ${min_strike:.2f} to ${max_strike:.2f}")

        # Evaluate pain at each strike price
        pain_results = []
        for strike in option_data['Strike'].values:
            total_payout, call_payout, put_payout = self.calculate_pain_at_price(strike, option_data)
            pain_results.append({
                'strike': strike,
                'total_payout': total_payout,
                'call_payout': call_payout,
                'put_payout': put_payout
            })

        # Find strike with minimum payout
        pain_df = pd.DataFrame(pain_results)
        min_pain_idx = pain_df['total_payout'].idxmin()
        max_pain_strike = pain_df.loc[min_pain_idx, 'strike']
        min_payout = pain_df.loc[min_pain_idx, 'total_payout']

        self.logger.info(f"Max pain calculated: ${max_pain_strike:.2f}")
        self.logger.debug(f"Minimum payout at max pain: ${min_payout:,.2f}")

        # Calculate percentage change
        pct_change = ((max_pain_strike - current_price) / current_price) * 100

        # Calculate net premium
        net_premium = self.calculate_net_premium(option_data, max_pain_strike)

        # Determine premium bias
        premium_bias = "call" if net_premium > 0 else "put" if net_premium < 0 else "neutral"

        # Calculate total OI
        total_call_oi = option_data['Call_OI'].sum()
        total_put_oi = option_data['Put_OI'].sum()

        result = {
            'max_pain_price': max_pain_strike,
            'current_price': current_price,
            'pct_change': pct_change,
            'net_call_put_premium': net_premium,
            'premium_bias': premium_bias,
            'total_call_oi': int(total_call_oi),
            'total_put_oi': int(total_put_oi),
            'min_payout': min_payout,
            'calculation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        return result

    def calculate_net_premium(self, option_data, max_pain_price):
        """
        Calculate net call/put premium

        Net Premium = Total Call Premium - Total Put Premium
        where premium is calculated based on open interest at max pain

        Args:
            option_data: DataFrame with Strike, Call_OI, Put_OI
            max_pain_price: Calculated max pain price

        Returns:
            float: Net premium (positive = more calls, negative = more puts)
        """
        # Calculate call premium: sum of call OI for strikes below max pain
        call_premium = 0
        for _, row in option_data.iterrows():
            if row['Strike'] < max_pain_price:
                call_premium += row['Call_OI'] * 100

        # Calculate put premium: sum of put OI for strikes above max pain
        put_premium = 0
        for _, row in option_data.iterrows():
            if row['Strike'] > max_pain_price:
                put_premium += row['Put_OI'] * 100

        net_premium = call_premium - put_premium

        self.logger.debug(f"Call premium: {call_premium:,.0f}, Put premium: {put_premium:,.0f}")
        self.logger.debug(f"Net premium: {net_premium:,.0f}")

        return net_premium

    def calculate_from_file(self, filepath):
        """
        Calculate max pain from CBOE CSV file

        Args:
            filepath: Path to CBOE CSV file

        Returns:
            dict with all results including ticker info
        """
        # Load data
        df, current_price, expiration_date, ticker = self.load_cboe_csv(filepath)

        # Parse option chain
        option_data = self.parse_option_chain(df)

        # Calculate max pain
        result = self.calculate_max_pain(option_data, current_price)

        # Add ticker and expiration info
        result['ticker'] = ticker
        result['expiration_date'] = expiration_date

        return result
