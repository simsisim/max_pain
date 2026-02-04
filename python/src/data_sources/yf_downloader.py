"""
Yahoo Finance Downloader

Handles batch downloading of option chain data and saving to local CSV files.
Implements download-first architecture for efficient multi-ticker processing.
"""

import os
import time
import pandas as pd
import yfinance as yf
from datetime import datetime
import logging


class YahooFinanceDownloader:
    """
    Downloads option chain data from Yahoo Finance and saves to CSV files
    
    Supports batch downloading with rate limiting, error handling, and 
    the ability to skip existing files.
    """
    
    def __init__(self, config):
        """
        Initialize downloader with configuration
        
        Args:
            config: dict with download-specific settings
        """
        self.config = config
        self.output_dir = config.get('download_dir', 'data/raw/yf')
        self.logger = logging.getLogger('max_pain.YahooFinanceDownloader')
        
        # Create output directory if needed
        os.makedirs(self.output_dir, exist_ok=True)
    
    def download_ticker(self, ticker, expiration_date):
        """
        Download option chain for single ticker
        
        Args:
            ticker: Stock ticker symbol (e.g., "NVDA")
            expiration_date: Expiration date string (YYYY-MM-DD or "next_monthly")
        
        Returns:
            dict with:
            - success: bool
            - filepath: str (if success)
            - error: str (if failed)
            - option_data_dict: dict (if success)
        """
        try:
            self.logger.info(f"Downloading {ticker} for expiration {expiration_date}")
            
            # Download from Yahoo Finance using yfinance
            option_data_dict = self._download_from_yf(ticker, expiration_date)
            
            # Save to CSV
            filepath = self.save_option_data(ticker, option_data_dict, expiration_date)
            
            self.logger.info(f"Saved to {os.path.basename(filepath)}")
            
            return {
                'success': True,
                'filepath': filepath,
                'option_data_dict': option_data_dict,
                'error': None
            }
            
        except Exception as e:
            self.logger.error(f"Failed to download {ticker}: {e}")
            return {
                'success': False,
                'filepath': None,
                'option_data_dict': None,
                'error': str(e)
            }
    
    def download_batch(self, tickers, expiration_date):
        """
        Download option chains for list of tickers
        
        Args:
            tickers: List of ticker symbols
            expiration_date: Expiration date for all tickers
        
        Returns:
            dict with:
            - succeeded: list of successful tickers
            - failed: dict {ticker: error_message}
            - filepaths: dict {ticker: filepath}
        """
        succeeded = []
        failed = {}
        filepaths = {}
        
        total = len(tickers)
        rate_limit = self.config.get('rate_limit_delay', 1)
        overwrite = self.config.get('overwrite_existing', False)
        
        self.logger.info(f"Starting batch download of {total} tickers")
        
        for i, ticker in enumerate(tickers, 1):
            print(f"  [{i}/{total}] Downloading {ticker}...")
            
            try:
                # Check if file exists
                if not overwrite:
                    existing_file = self._find_existing_file(ticker, expiration_date)
                    if existing_file:
                        print(f"    ↻ Using existing file")
                        filepaths[ticker] = existing_file
                        succeeded.append(ticker)
                        continue
                
                # Download ticker
                result = self.download_ticker(ticker, expiration_date)
                
                if result['success']:
                    print(f"    ✓ Saved to {os.path.basename(result['filepath'])}")
                    succeeded.append(ticker)
                    filepaths[ticker] = result['filepath']
                else:
                    print(f"    ✗ Failed: {result['error']}")
                    failed[ticker] = result['error']
                
                # Rate limiting (don't delay after last ticker)
                if i < total:
                    time.sleep(rate_limit)
                    
            except Exception as e:
                print(f"    ✗ Error: {e}")
                failed[ticker] = str(e)
        
        return {
            'succeeded': succeeded,
            'failed': failed,
            'filepaths': filepaths
        }
    
    def save_option_data(self, ticker, option_data_dict, expiration_date):
        """
        Save option data to CSV file with metadata header
        
        Args:
            ticker: Stock ticker symbol
            option_data_dict: dict with ticker, current_price, expiration_date, option_data
            expiration_date: Expiration date (for filename)
        
        Returns:
            filepath: str - path to saved CSV file
        """
        # Generate filename
        exp_date_str = option_data_dict['expiration_date'].replace('-', '')
        filename = f"{ticker}_{exp_date_str}_optionchain.csv"
        filepath = os.path.join(self.output_dir, filename)
        
        # Write metadata header
        with open(filepath, 'w') as f:
            f.write(f"Ticker,{ticker}\n")
            f.write(f"CurrentPrice,{option_data_dict['current_price']}\n")
            f.write(f"ExpirationDate,{option_data_dict['expiration_date']}\n")
            f.write(f"DownloadTimestamp,{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("\n")  # Separator
        
        # Append option data
        option_data_dict['option_data'].to_csv(
            filepath,
            mode='a',  # Append mode
            index=False
        )
        
        self.logger.debug(f"Saved {len(option_data_dict['option_data'])} strikes to {filepath}")
        
        return filepath
    
    def load_option_data(self, filepath):
        """
        Load previously downloaded option data from CSV
        
        Args:
            filepath: Path to CSV file
        
        Returns:
            dict with ticker, current_price, expiration_date, option_data
        """
        self.logger.debug(f"Loading option data from {filepath}")
        
        # Read metadata (first 4 lines)
        metadata = {}
        with open(filepath, 'r') as f:
            for i in range(4):
                line = f.readline().strip()
                if ',' in line:
                    key, value = line.split(',', 1)
                    metadata[key] = value
        
        # Read option data (skip metadata + blank line = 5 rows)
        option_data = pd.read_csv(filepath, skiprows=5)
        
        # Ensure correct data types
        option_data['Strike'] = pd.to_numeric(option_data['Strike'])
        option_data['Call_OI'] = pd.to_numeric(option_data['Call_OI']).astype(int)
        option_data['Put_OI'] = pd.to_numeric(option_data['Put_OI']).astype(int)
        
        result = {
            'ticker': metadata['Ticker'],
            'current_price': float(metadata['CurrentPrice']),
            'expiration_date': metadata['ExpirationDate'],
            'option_data': option_data
        }
        
        self.logger.info(f"Loaded {len(option_data)} strikes for {metadata['Ticker']}")
        
        return result
    
    def _download_from_yf(self, ticker, expiration_date):
        """
        Download option chain from Yahoo Finance API
        
        This reuses the logic from YahooFinanceAdapter but returns
        the data instead of processing it.
        """
        # Import here to avoid circular dependency
        from .yf_adapter import YahooFinanceAdapter
        
        # Create temporary adapter to use its download logic
        adapter = YahooFinanceAdapter(self.config)
        
        # Use adapter's fetch method to get data
        option_data_dict = adapter.fetch_option_data(ticker, expiration_date)
        
        return option_data_dict
    
    def _find_existing_file(self, ticker, expiration_date):
        """
        Find existing CSV file for ticker and expiration
        
        Returns:
            filepath if found, None otherwise
        """
        # Try to match on ticker and expiration in filename
        # Filename format: TICKER_YYYYMMDD_optionchain.csv
        
        # Normalize expiration date
        if expiration_date == 'next_monthly':
            # Can't match, return None
            return None
        
        exp_str = expiration_date.replace('-', '')
        pattern = f"{ticker}_{exp_str}_optionchain.csv"
        
        filepath = os.path.join(self.output_dir, pattern)
        
        if os.path.exists(filepath):
            self.logger.debug(f"Found existing file: {filepath}")
            return filepath
        
        return None
