"""
Yahoo Finance data adapter

Downloads and transforms Yahoo Finance option data to common format.
"""

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from .base import OptionDataAdapter


class YahooFinanceAdapter(OptionDataAdapter):
    """
    Adapter for Yahoo Finance data via yfinance library
    
    Downloads option chain data and transforms it into common format.
    Key feature: merges separate calls and puts DataFrames on strike price.
    """
    
    def fetch_option_data(self, ticker, expiration_date):
        """
        Download option data from Yahoo Finance
        
        Args:
            ticker: Stock ticker symbol (e.g., "NVDA")
            expiration_date: Expiration date (YYYY-MM-DD) or "next_monthly"
        
        Returns:
            dict with ticker, current_price, expiration_date, option_data
        """
        self.logger.info(f"Downloading Yahoo Finance data for {ticker}")
        
        # Create ticker object
        yf_ticker = yf.Ticker(ticker)
        
        # Get current price
        current_price = self._get_current_price(yf_ticker)
        
        # Get available expirations
        available_expirations = list(yf_ticker.options)
        
        if not available_expirations:
            raise ValueError(f"No option expirations available for {ticker}")
        
        # Select appropriate expiration
        selected_expiration = self._select_expiration(
            available_expirations,
            expiration_date,
            self.config.get('expiration_selection', 'nearest')
        )
        
        self.logger.info(f"Selected expiration: {selected_expiration}")
        
        # Download option chain
        opt_chain = yf_ticker.option_chain(selected_expiration)
        
        # Extract and merge calls and puts
        option_data = self._merge_option_chain(opt_chain.calls, opt_chain.puts)
        
        # Validate
        self.validate_option_data(option_data)
        
        return {
            'ticker': ticker,
            'current_price': current_price,
            'expiration_date': selected_expiration,
            'option_data': option_data
        }
    
    def get_available_expirations(self, ticker):
        """
        Get available expiration dates from Yahoo Finance
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            list of expiration date strings (YYYY-MM-DD)
        """
        try:
            yf_ticker = yf.Ticker(ticker)
            return list(yf_ticker.options)
        except Exception as e:
            self.logger.error(f"Error getting expirations for {ticker}: {e}")
            return []
    
    def _get_current_price(self, yf_ticker):
        """Get current stock price from ticker object"""
        try:
            # Try from info dict
            current_price = yf_ticker.info.get('currentPrice')
            
            if current_price is None or current_price == 0:
                # Fallback to recent history
                hist = yf_ticker.history(period='1d')
                if len(hist) > 0:
                    current_price = hist['Close'].iloc[-1]
            
            if current_price is None or current_price == 0:
                raise ValueError("Could not retrieve current price")
            
            self.logger.debug(f"Current price: ${current_price:.2f}")
            return float(current_price)
            
        except Exception as e:
            raise ValueError(f"Error getting current price: {e}")
    
    def _select_expiration(self, available_expirations, requested_date, strategy):
        """
        Select best matching expiration date
        
        Args:
            available_expirations: List of date strings from YF
            requested_date: Requested date string or "next_monthly"
            strategy: 'nearest', 'next_available', or 'exact'
        
        Returns:
            Selected expiration date string
        """
        if requested_date.lower() == 'next_3fr_monthly':
            # Find next monthly expiration (3rd Friday logic)
            from ..utils import get_next_monthly_expiration
            target_date = get_next_monthly_expiration()
            target_str = target_date.strftime('%Y-%m-%d')
            self.logger.debug(f"Looking for monthly expiration near {target_str}")
        else:
            target_str = requested_date
        
        if strategy == 'exact':
            # Must match exactly
            if target_str in available_expirations:
                return target_str
            else:
                raise ValueError(f"Exact expiration {target_str} not available. Available: {available_expirations}")
        
        else:  # nearest or next_available
            # Find closest match
            target_date = datetime.strptime(target_str, '%Y-%m-%d')
            exp_dates = [datetime.strptime(d, '%Y-%m-%d') for d in available_expirations]
            
            if strategy == 'next_available':
                # Find first date on or after target
                future_dates = [d for d in exp_dates if d >= target_date]
                if future_dates:
                    selected = min(future_dates)
                else:
                    # No future dates, use last available
                    selected = max(exp_dates)
            else:  # nearest
                # Find date with minimum distance
                selected = min(exp_dates, key=lambda d: abs((d - target_date).days))
            
            selected_str = selected.strftime('%Y-%m-%d')
            self.logger.debug(f"Selected {selected_str} as closest to {target_str}")
            
            return selected_str
    
    def _merge_option_chain(self, calls_df, puts_df):
        """
        Merge calls and puts DataFrames into common format

        This is the CRITICAL transformation for Yahoo Finance data:
        - YF provides separate DataFrames for calls and puts
        - We need to merge them on strike price
        - Then rename to standard column names

        Args:
            calls_df: Calls DataFrame from yfinance
            puts_df: Puts DataFrame from yfinance

        Returns:
            DataFrame with columns: Strike, Call_OI, Put_OI
            (plus Call_Gamma, Put_Gamma if gamma is available — Mod 5)
        """
        self.logger.debug(f"Merging option chain: {len(calls_df)} calls, {len(puts_df)} puts")

        # Extract needed columns; capture gamma (Mod 5) and volume (Mod 6) when available
        calls_cols = ['strike', 'openInterest']
        puts_cols = ['strike', 'openInterest']

        has_gamma = 'gamma' in calls_df.columns and 'gamma' in puts_df.columns
        if has_gamma:
            calls_cols.append('gamma')
            puts_cols.append('gamma')

        has_volume = 'volume' in calls_df.columns and 'volume' in puts_df.columns
        if has_volume:
            calls_cols.append('volume')
            puts_cols.append('volume')

        calls = calls_df[calls_cols].copy()
        puts = puts_df[puts_cols].copy()

        # CRITICAL: Merge on strike price with outer join
        # This ensures we keep all strikes even if calls or puts are missing
        option_data = pd.merge(
            calls,
            puts,
            on='strike',
            suffixes=('_call', '_put'),
            how='outer'  # Keep all strikes
        )

        # Rename to standard column names
        rename_map = {
            'strike': 'Strike',
            'openInterest_call': 'Call_OI',
            'openInterest_put': 'Put_OI',
        }
        if has_gamma:
            rename_map['gamma_call'] = 'Call_Gamma'
            rename_map['gamma_put'] = 'Put_Gamma'
        if has_volume:
            rename_map['volume_call'] = 'Call_Volume'
            rename_map['volume_put'] = 'Put_Volume'
        option_data.rename(columns=rename_map, inplace=True)

        # Fill missing values with 0 (pandas 3.0 compatible)
        fill_map = {'Call_OI': 0, 'Put_OI': 0}
        if has_gamma:
            fill_map['Call_Gamma'] = 0.0
            fill_map['Put_Gamma'] = 0.0
        if has_volume:
            fill_map['Call_Volume'] = 0
            fill_map['Put_Volume'] = 0
        option_data = option_data.fillna(fill_map)

        # Ensure numeric types
        option_data['Strike'] = pd.to_numeric(option_data['Strike'])
        option_data['Call_OI'] = pd.to_numeric(option_data['Call_OI']).astype(int)
        option_data['Put_OI'] = pd.to_numeric(option_data['Put_OI']).astype(int)
        if has_gamma:
            option_data['Call_Gamma'] = pd.to_numeric(option_data['Call_Gamma'])
            option_data['Put_Gamma'] = pd.to_numeric(option_data['Put_Gamma'])
        if has_volume:
            option_data['Call_Volume'] = pd.to_numeric(option_data['Call_Volume']).astype(int)
            option_data['Put_Volume'] = pd.to_numeric(option_data['Put_Volume']).astype(int)

        # Sort by strike and reset index
        option_data.sort_values('Strike', inplace=True)
        option_data.reset_index(drop=True, inplace=True)

        self.logger.info(f"Merged option chain: {len(option_data)} strikes")
        self.logger.debug(f"Strike range: ${option_data['Strike'].min():.2f} - ${option_data['Strike'].max():.2f}")
        if has_gamma:
            self.logger.debug("Gamma columns captured: Call_Gamma, Put_Gamma")
        if has_volume:
            self.logger.debug("Volume columns captured: Call_Volume, Put_Volume")

        return option_data
