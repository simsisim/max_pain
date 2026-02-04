"""
CBOE data adapter

Adapts CBOE CSV files to common option data format.
"""

import os
import pandas as pd
from datetime import datetime
from .base import OptionDataAdapter


class CBOEAdapter(OptionDataAdapter):
    """
    Adapter for CBOE CSV files
    
    Transforms CBOE CSV format into common option data format.
    """
    
    def fetch_option_data(self, ticker, expiration_date):
        """
        Load option data from CBOE CSV file
        
        Args:
            ticker: Stock ticker symbol
            expiration_date: Expiration date (YYYY-MM-DD) or "next_monthly"
        
        Returns:
            dict with ticker, current_price, expiration_date, option_data
        """
        self.logger.info(f"Fetching CBOE data for {ticker}")
        
        # Find CSV file
        data_dir = self.config.get('data_dir', 'data/raw/cboe')
        csv_file = self._find_csv_file(ticker, expiration_date, data_dir)
        
        # Load and parse CSV
        df, current_price, actual_expiration, ticker_parsed = self._load_cboe_csv(csv_file)
        option_data = self._parse_option_chain(df)
        
        # Validate
        self.validate_option_data(option_data)
        
        return {
            'ticker': ticker_parsed or ticker,
            'current_price': current_price,
            'expiration_date': actual_expiration,
            'option_data': option_data
        }
    
    def get_available_expirations(self, ticker):
        """
        Get available expirations from CSV files in data directory
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            list of expiration date strings
        """
        data_dir = self.config.get('data_dir', 'data/raw/cboe')
        
        if not os.path.exists(data_dir):
            return []
        
        # Look for CSV files matching ticker
        files = [f for f in os.listdir(data_dir) 
                if f.lower().endswith('.csv') and ticker.lower() in f.lower()]
        
        expirations = []
        for file in files:
            try:
                filepath = os.path.join(data_dir, file)
                df = pd.read_csv(filepath, skiprows=3, nrows=1)
                if 'Expiration Date' in df.columns:
                    exp_date = df['Expiration Date'].iloc[0]
                    expirations.append(exp_date)
            except Exception as e:
                self.logger.warning(f"Could not parse expiration from {file}: {e}")
        
        return expirations
    
    def _find_csv_file(self, ticker, expiration_date, data_dir):
        """Find appropriate CSV file for ticker and expiration"""
        if not os.path.exists(data_dir):
            raise FileNotFoundError(f"Data directory not found: {data_dir}")
        
        # Look for files matching ticker
        csv_files = [f for f in os.listdir(data_dir) 
                    if f.lower().endswith('.csv') and ticker.lower() in f.lower()]
        
        if not csv_files:
            raise FileNotFoundError(f"No CBOE CSV files found for {ticker} in {data_dir}")
        
        # For now, use first matching file
        # TODO: Add date matching logic for specific expirations
        csv_file = os.path.join(data_dir, csv_files[0])
        self.logger.debug(f"Using CSV file: {csv_file}")
        
        return csv_file
    
    def _load_cboe_csv(self, filepath):
        """
        Load CBOE option chain data from CSV file
        (Extracted from MaxPainCalculator.load_cboe_csv)
        
        Returns:
            tuple: (option_chain_df, current_price, expiration_date, ticker)
        """
        self.logger.debug(f"Loading CBOE CSV: {filepath}")
        
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        # Find price information line
        header_line = None
        skip_rows = 0
        for i, line in enumerate(lines):
            if 'Last:' in line:
                header_line = line.strip()
                skip_rows = i + 2
                break
        
        if not header_line:
            raise ValueError("Could not find price information in CSV")
        
        # Parse company name and price
        parts = header_line.split(',')
        company_name = parts[0] if parts else "Unknown"
        ticker_parts = company_name.strip().split()
        ticker = ticker_parts[0].upper() if ticker_parts else "UNKNOWN"
        
        last_price_str = parts[1].replace('Last:', '').strip() if len(parts) > 1 else "0"
        current_price = float(last_price_str)
        
        # Read option chain data
        df = pd.read_csv(filepath, skiprows=skip_rows)
        
        # Extract expiration date
        expiration_date = df['Expiration Date'].iloc[0] if 'Expiration Date' in df.columns else None
        
        return df, current_price, expiration_date, ticker
    
    def _parse_option_chain(self, df):
        """
        Parse option chain DataFrame and extract relevant data
        (Extracted from MaxPainCalculator.parse_option_chain)
        
        Returns:
            DataFrame with columns: Strike, Call_OI, Put_OI
        """
        strikes = df['Strike'].values
        call_oi = df['Open Interest'].values
        
        # Put OI is second "Open Interest" column
        if 'Open Interest.1' in df.columns:
            put_oi = df['Open Interest.1'].values
        else:
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
        
        # Clean data
        option_data['Strike'] = pd.to_numeric(option_data['Strike'], errors='coerce')
        option_data['Call_OI'] = pd.to_numeric(option_data['Call_OI'], errors='coerce').fillna(0)
        option_data['Put_OI'] = pd.to_numeric(option_data['Put_OI'], errors='coerce').fillna(0)
        
        # Remove invalid strikes
        option_data = option_data.dropna(subset=['Strike'])
        option_data = option_data[option_data['Strike'] > 0]
        
        self.logger.info(f"Parsed {len(option_data)} valid option strikes")
        
        return option_data
