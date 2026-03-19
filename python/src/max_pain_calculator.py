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

    Optional enhancements (controlled via config or kwargs):
    - Mod 1: Strike band filter (±N% around spot)
    - Mod 2: Minimum OI threshold
    - Mod 3: Dollar-weighted OI
    - Mod 4: Smooth pain curve (rolling average)
    - Mod 5: Net gamma computation (requires Call_Gamma/Put_Gamma columns)
    """

    def __init__(self, config=None):
        """
        Args:
            config: Optional dict with calculation parameters.
                    Keys: strike_band_pct, min_open_interest, dollar_weighted_oi,
                          smooth_pain_curve, smoothing_window
        """
        self.config = config or {}
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

    def _apply_dollar_weight(self, option_data):
        """
        Add dollar-notional-weighted OI columns (Mod 3).

        Call_OI_W = Call_OI × Strike
        Put_OI_W  = Put_OI  × Strike

        Args:
            option_data: DataFrame with Strike, Call_OI, Put_OI

        Returns:
            New DataFrame with additional Call_OI_W and Put_OI_W columns
        """
        weighted = option_data.copy()
        weighted['Call_OI_W'] = weighted['Call_OI'] * weighted['Strike']
        weighted['Put_OI_W'] = weighted['Put_OI'] * weighted['Strike']
        return weighted

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

    def calculate_max_pain(self, option_data, current_price,
                           strike_band_pct=15, min_open_interest=10,
                           dollar_weighted_oi=False,
                           volume_weighted_oi=False,
                           smooth_pain_curve=False, smoothing_window=3):
        """
        Calculate max pain price

        Args:
            option_data: DataFrame with Strike, Call_OI, Put_OI
                         (optionally Call_Gamma, Put_Gamma for Mod 5;
                          optionally Call_Volume, Put_Volume for Mod 6)
            current_price: Current stock price
            strike_band_pct: Filter strikes to ±N% of spot (0 = disabled) [Mod 1]
            min_open_interest: Drop strikes with total OI below this (0 = disabled) [Mod 2]
            dollar_weighted_oi: Weight by dollar notional (OI × Strike) [Mod 3]
            volume_weighted_oi: Substitute today's volume for OI in the formula [Mod 6]
                                Falls back to OI with a warning if volume is absent or all-zero.
                                Composes with dollar_weighted_oi → Volume × Strike.
            smooth_pain_curve: Apply rolling-average smoothing before finding min [Mod 4]
            smoothing_window: Window size for rolling average [Mod 4]

        Returns:
            dict with calculation results (includes net_gamma_data if gamma columns present)
        """
        self.logger.info("Calculating max pain price")

        # Work on a copy so the caller's DataFrame is not modified
        option_data = option_data.copy()

        # --- Mod 1: Strike band filter ---
        if strike_band_pct > 0:
            band = strike_band_pct / 100.0
            lo = current_price * (1.0 - band)
            hi = current_price * (1.0 + band)
            before = len(option_data)
            option_data = option_data[
                (option_data['Strike'] >= lo) & (option_data['Strike'] <= hi)
            ].copy()
            dropped = before - len(option_data)
            if dropped:
                self.logger.info(
                    f"Strike band filter (±{strike_band_pct}%): "
                    f"dropped {dropped} strikes outside "
                    f"[${lo:.2f}, ${hi:.2f}]"
                )

        # --- Mod 2: Minimum OI threshold ---
        if min_open_interest > 0:
            before = len(option_data)
            option_data = option_data[
                (option_data['Call_OI'] + option_data['Put_OI']) >= min_open_interest
            ].copy()
            dropped = before - len(option_data)
            if dropped:
                self.logger.info(
                    f"Min OI filter (>={min_open_interest}): "
                    f"dropped {dropped} low-OI strikes"
                )

        if option_data.empty:
            raise ValueError(
                "No option data remaining after strike band / OI filters. "
                "Try increasing strike_band_pct or reducing min_open_interest."
            )

        self.logger.debug(
            f"Evaluating {len(option_data)} strikes from "
            f"${option_data['Strike'].min():.2f} to ${option_data['Strike'].max():.2f}"
        )

        # --- Mod 5: Net gamma (before dollar-weighting copy) ---
        has_gamma = (
            'Call_Gamma' in option_data.columns
            and 'Put_Gamma' in option_data.columns
        )
        if has_gamma:
            option_data['Net_Gamma'] = (
                option_data['Call_OI'] * option_data['Call_Gamma']
                - option_data['Put_OI'] * option_data['Put_Gamma']
            )
            self.logger.debug("Computed Net_Gamma per strike")

        # --- Mod 6: Volume-weighted OI ---
        # Build calc_data (separate copy so original OI/totals are preserved).
        # When enabled, today's volume replaces OI as the weighting signal.
        # Falls back to OI when volume is absent or all-zero (pre-market).
        # Runs before Mod 3 so dollar-weighting composes on top: Volume × Strike.
        calc_data = option_data.copy()
        if volume_weighted_oi:
            has_vol_cols = (
                'Call_Volume' in option_data.columns
                and 'Put_Volume' in option_data.columns
            )
            total_volume = (
                int(option_data['Call_Volume'].sum() + option_data['Put_Volume'].sum())
                if has_vol_cols else 0
            )
            if has_vol_cols and total_volume > 0:
                calc_data['Call_OI'] = option_data['Call_Volume']
                calc_data['Put_OI'] = option_data['Put_Volume']
                self.logger.debug(
                    f"Volume-weighted OI: substituted Call_Volume/Put_Volume "
                    f"(total volume {total_volume:,})"
                )
            else:
                self.logger.warning(
                    "volume_weighted_oi=True but volume data is absent or all-zero "
                    "(pre-market / no trades yet?); falling back to open interest"
                )

        # --- Mod 3: Dollar-weighted OI ---
        # Applied on top of calc_data so it composes with Mod 6:
        # both enabled → Volume × Strike ("dollar-volume weighting").
        if dollar_weighted_oi:
            calc_data = self._apply_dollar_weight(calc_data)
            calc_data['Call_OI'] = calc_data['Call_OI_W']
            calc_data['Put_OI'] = calc_data['Put_OI_W']
            self.logger.debug(
                "Dollar-weighted OI applied%s" %
                (" (on top of volume)" if volume_weighted_oi else "")
            )

        # Evaluate pain at each strike price
        pain_results = []
        for strike in calc_data['Strike'].values:
            total_payout, call_payout, put_payout = self.calculate_pain_at_price(strike, calc_data)
            pain_results.append({
                'strike': strike,
                'total_payout': total_payout,
                'call_payout': call_payout,
                'put_payout': put_payout
            })

        pain_df = pd.DataFrame(pain_results)

        # --- Mod 4: Smooth pain curve ---
        if smooth_pain_curve and len(pain_df) >= 3:
            pain_df['total_payout_smooth'] = pain_df['total_payout'].rolling(
                window=smoothing_window, center=True, min_periods=1
            ).mean()
            min_pain_idx = pain_df['total_payout_smooth'].idxmin()
            self.logger.debug(
                f"Pain curve smoothed (window={smoothing_window})"
            )
        else:
            min_pain_idx = pain_df['total_payout'].idxmin()

        max_pain_strike = pain_df.loc[min_pain_idx, 'strike']
        min_payout = pain_df.loc[min_pain_idx, 'total_payout']

        self.logger.info(f"Max pain calculated: ${max_pain_strike:.2f}")
        self.logger.debug(f"Minimum payout at max pain: ${min_payout:,.2f}")

        # Calculate percentage change
        pct_change = ((max_pain_strike - current_price) / current_price) * 100

        # Calculate net premium (uses original unweighted OI)
        net_premium = self.calculate_net_premium(option_data, max_pain_strike)

        # Determine premium bias
        premium_bias = "call" if net_premium > 0 else "put" if net_premium < 0 else "neutral"

        # Calculate total OI (original unweighted)
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

        # Include net gamma data for chart overlay (Mod 5)
        if has_gamma:
            result['net_gamma_data'] = (
                option_data.set_index('Strike')['Net_Gamma']
            )

        return result

    def calculate_net_premium(self, option_data, max_pain_price):
        """
        Calculate net call/put premium in dollars (dollar notional).

        Net Premium ($) = Σ(Call_OI × 100 × Strike) for ITM calls at max pain
                        − Σ(Put_OI  × 100 × Strike) for ITM puts  at max pain

        ITM calls: Strike < max_pain_price
        ITM puts:  Strike > max_pain_price

        Multiplying by Strike converts contract count → dollar notional,
        matching the EarningsBeats report scale.

        Args:
            option_data: DataFrame with Strike, Call_OI, Put_OI
            max_pain_price: Calculated max pain price

        Returns:
            float: Net premium in dollars (positive = call-heavy, negative = put-heavy)
        """
        itm_calls = option_data[option_data['Strike'] < max_pain_price]
        itm_puts  = option_data[option_data['Strike'] > max_pain_price]

        call_premium = (itm_calls['Call_OI'] * 100 * itm_calls['Strike']).sum()
        put_premium  = (itm_puts['Put_OI']   * 100 * itm_puts['Strike']).sum()

        net_premium = call_premium - put_premium

        self.logger.debug(f"Call premium: ${call_premium:,.0f}, Put premium: ${put_premium:,.0f}")
        self.logger.debug(f"Net premium:  ${net_premium:,.0f}")

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

        # Calculate max pain (kwargs pick up self.config defaults if caller passes them)
        result = self.calculate_max_pain(option_data, current_price)

        # Add ticker and expiration info
        result['ticker'] = ticker
        result['expiration_date'] = expiration_date

        return result
