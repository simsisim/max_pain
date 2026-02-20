"""
CBOE Downloader

Handles batch downloading of option chain CSV files from CBOE.
Implements download-first architecture mirroring YahooFinanceDownloader.
"""

import os
import time
import logging
import requests


class CBOEDownloader:
    """
    Downloads option chain CSV data from CBOE and saves to local files.

    Supports batch downloading with rate limiting, error handling, and
    the ability to skip existing files.
    """

    # URL template for CBOE delayed-quote option chain CSV
    DOWNLOAD_URL = "https://www.cboe.com/delayed_quotes/{ticker}/download_csv?market=option"

    # Browser-like User-Agent to avoid 403 responses
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    def __init__(self, config):
        """
        Initialize downloader with configuration.

        Args:
            config: dict with CBOE-specific settings
        """
        self.config = config
        self.output_dir = config.get('data_dir', 'data/raw/cboe')
        self.rate_limit = config.get('rate_limit_delay', 2)
        self.timeout = config.get('request_timeout', 30)
        self.logger = logging.getLogger('max_pain.CBOEDownloader')

        os.makedirs(self.output_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def download_ticker(self, ticker):
        """
        Download option chain CSV for a single ticker.

        Args:
            ticker: Stock ticker symbol (e.g. "NVDA")

        Returns:
            dict with:
            - success: bool
            - filepath: str | None
            - error: str | None
        """
        ticker = ticker.upper()
        url = self.DOWNLOAD_URL.format(ticker=ticker.lower())
        filepath = os.path.join(self.output_dir, f"{ticker.lower()}_quotedata.csv")

        try:
            self.logger.info(f"Downloading CBOE data for {ticker} from {url}")
            response = requests.get(url, headers=self.HEADERS, timeout=self.timeout)
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                f.write(response.content)

            self.logger.info(f"Saved {ticker} to {os.path.basename(filepath)}")
            return {'success': True, 'filepath': filepath, 'error': None}

        except requests.HTTPError as e:
            msg = f"HTTP {e.response.status_code}: {e}"
            self.logger.error(f"Failed to download {ticker}: {msg}")
            return {'success': False, 'filepath': None, 'error': msg}
        except Exception as e:
            self.logger.error(f"Failed to download {ticker}: {e}")
            return {'success': False, 'filepath': None, 'error': str(e)}

    def download_batch(self, tickers):
        """
        Download option chain CSVs for a list of tickers.

        Args:
            tickers: List of ticker symbols

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
        overwrite = self.config.get('overwrite_existing', False)

        self.logger.info(f"Starting CBOE batch download of {total} tickers")

        for i, ticker in enumerate(tickers, 1):
            ticker = ticker.upper()
            print(f"  [{i}/{total}] Downloading {ticker}...")

            try:
                # Skip if file already exists and overwrite is disabled
                if not overwrite:
                    existing = self._find_existing_file(ticker)
                    if existing:
                        print(f"    ↻ Using existing file")
                        filepaths[ticker] = existing
                        succeeded.append(ticker)
                        continue

                result = self.download_ticker(ticker)

                if result['success']:
                    print(f"    ✓ Saved to {os.path.basename(result['filepath'])}")
                    succeeded.append(ticker)
                    filepaths[ticker] = result['filepath']
                else:
                    print(f"    ✗ Failed: {result['error']}")
                    failed[ticker] = result['error']

                # Rate limiting (skip delay after last ticker)
                if i < total:
                    time.sleep(self.rate_limit)

            except Exception as e:
                print(f"    ✗ Error: {e}")
                failed[ticker] = str(e)

        return {
            'succeeded': succeeded,
            'failed': failed,
            'filepaths': filepaths
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _find_existing_file(self, ticker):
        """
        Check whether a previously downloaded CSV file exists for ticker.

        Returns:
            filepath string if found, None otherwise
        """
        filepath = os.path.join(self.output_dir, f"{ticker.lower()}_quotedata.csv")
        if os.path.exists(filepath):
            self.logger.debug(f"Found existing file: {filepath}")
            return filepath
        return None
