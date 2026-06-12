"""
CBOE JSON Downloader

Fetches option chain data from CBOE's public delayed-quotes JSON API:
  https://cdn.cboe.com/api/global/delayed_quotes/options/{TICKER}.json

This API serves the last EOD snapshot (published ~15:45 ET) regardless of
time of day, solving the yfinance zero-OI problem for after-hours manual runs.

Saves CSVs in the same 5-line-header format as YahooFinanceDownloader so
Phase 2 can call YahooFinanceDownloader.load_option_data() unchanged.
"""

import os
import re
import time
import logging
import requests
import pandas as pd
from datetime import datetime


class CBOEJsonDownloader:

    BASE_URL = "https://cdn.cboe.com/api/global/delayed_quotes/options/{ticker}.json"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
    }

    def __init__(self, config):
        self.config = config
        self.output_dir = config.get('download_dir', 'data/raw/cboe_json')
        self.rate_limit = config.get('rate_limit_delay', 1)
        self.timeout = config.get('request_timeout', 30)
        self.logger = logging.getLogger('max_pain.CBOEJsonDownloader')
        os.makedirs(self.output_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API — mirrors YahooFinanceDownloader
    # ------------------------------------------------------------------

    def download_ticker(self, ticker, expiration_date):
        """
        Fetch option chain for a single ticker from the CBOE JSON API.

        Returns:
            dict with success, filepath, option_data_dict, error
        """
        ticker = ticker.upper()
        url = self.BASE_URL.format(ticker=ticker)
        try:
            self.logger.info(f"Downloading CBOE JSON data for {ticker}")
            response = requests.get(url, headers=self.HEADERS, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            option_data_dict = self._parse_response(ticker, data, expiration_date)
            filepath = self._save_option_data(ticker, option_data_dict)
            self.logger.info(f"Saved to {os.path.basename(filepath)}")
            return {'success': True, 'filepath': filepath,
                    'option_data_dict': option_data_dict, 'error': None}
        except Exception as e:
            self.logger.error(f"Failed to download {ticker}: {e}")
            return {'success': False, 'filepath': None,
                    'option_data_dict': None, 'error': str(e)}

    def download_batch(self, tickers, expiration_date):
        """
        Download option chains for a list of tickers.

        Returns:
            dict with succeeded (list), failed (dict), filepaths (dict)
        """
        succeeded = []
        failed = {}
        filepaths = {}
        total = len(tickers)
        overwrite = self.config.get('overwrite_existing', False)

        self.logger.info(f"Starting CBOE JSON batch download of {total} tickers")

        for i, ticker in enumerate(tickers, 1):
            ticker = ticker.upper()
            print(f"  [{i}/{total}] Downloading {ticker}...")
            try:
                if not overwrite:
                    existing = self._find_existing_file(ticker, expiration_date)
                    if existing:
                        print(f"    ↻ Using existing file")
                        filepaths[ticker] = existing
                        succeeded.append(ticker)
                        continue

                result = self.download_ticker(ticker, expiration_date)

                if result['success']:
                    print(f"    ✓ Saved to {os.path.basename(result['filepath'])}")
                    succeeded.append(ticker)
                    filepaths[ticker] = result['filepath']
                else:
                    print(f"    ✗ Failed: {result['error']}")
                    failed[ticker] = result['error']

                if i < total:
                    time.sleep(self.rate_limit)

            except Exception as e:
                print(f"    ✗ Error: {e}")
                failed[ticker] = str(e)

        return {'succeeded': succeeded, 'failed': failed, 'filepaths': filepaths}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_response(self, ticker, data, expiration_date):
        """
        Parse CBOE JSON into the standard option_data_dict format.

        CBOE response structure:
          data['data']['options'] — list of option records
          data['data']['current_price'] — underlying spot price
        """
        cboe_data = data.get('data', data)

        options_list = cboe_data.get('options', [])
        if not options_list:
            raise ValueError(f"No options data in CBOE response for {ticker}")

        current_price = (
            cboe_data.get('current_price') or
            cboe_data.get('close') or
            cboe_data.get('last_trade_price')
        )
        if not current_price:
            raise ValueError(f"Could not find current price in CBOE response for {ticker}")
        current_price = float(current_price)

        target_exp = self._resolve_expiration(options_list, expiration_date)

        calls, puts = {}, {}
        call_volumes, put_volumes = {}, {}
        call_gammas, put_gammas = {}, {}

        for opt in options_list:
            parsed = self._parse_option_symbol(opt.get('option', ''))
            if parsed is None:
                continue
            sym_exp, opt_type, strike = parsed
            if sym_exp != target_exp:
                continue

            oi     = int(float(opt.get('open_interest', 0) or 0))
            volume = int(float(opt.get('volume', 0) or 0))
            gamma  = float(opt.get('gamma', 0.0) or 0.0)

            if opt_type == 'C':
                calls[strike]        = oi
                call_volumes[strike] = volume
                call_gammas[strike]  = gamma
            else:
                puts[strike]        = oi
                put_volumes[strike] = volume
                put_gammas[strike]  = gamma

        if not calls and not puts:
            raise ValueError(
                f"No options found for expiration {target_exp} in CBOE data for {ticker}"
            )

        all_strikes = sorted(set(calls.keys()) | set(puts.keys()))
        has_gamma = any(
            v != 0.0
            for v in list(call_gammas.values()) + list(put_gammas.values())
        )

        rows = []
        for strike in all_strikes:
            row = {
                'Strike':       strike,
                'Call_OI':      calls.get(strike, 0),
                'Put_OI':       puts.get(strike, 0),
                'Call_Volume':  call_volumes.get(strike, 0),
                'Put_Volume':   put_volumes.get(strike, 0),
            }
            if has_gamma:
                row['Call_Gamma'] = call_gammas.get(strike, 0.0)
                row['Put_Gamma']  = put_gammas.get(strike, 0.0)
            rows.append(row)

        option_data = pd.DataFrame(rows)
        self.logger.info(
            f"CBOE JSON: {len(option_data)} strikes for {ticker} exp {target_exp}"
        )

        return {
            'ticker':          ticker,
            'current_price':   current_price,
            'expiration_date': target_exp,
            'option_data':     option_data,
        }

    def _resolve_expiration(self, options_list, expiration_date):
        """Select the nearest available expiration to the requested date."""
        expirations = set()
        for opt in options_list:
            parsed = self._parse_option_symbol(opt.get('option', ''))
            if parsed:
                expirations.add(parsed[0])

        if not expirations:
            raise ValueError("Could not parse any expiration dates from CBOE options")

        if expiration_date.lower() == 'next_3fr_monthly':
            from src.utils import get_next_monthly_expiration
            target = get_next_monthly_expiration().strftime('%Y-%m-%d')
        elif expiration_date.lower() == 'current_3fr_monthly':
            from src.utils import get_current_monthly_expiration
            target = get_current_monthly_expiration().strftime('%Y-%m-%d')
        else:
            target = expiration_date

        target_dt  = datetime.strptime(target, '%Y-%m-%d')
        avail_dts  = [datetime.strptime(d, '%Y-%m-%d') for d in expirations]
        selected   = min(avail_dts, key=lambda d: abs((d - target_dt).days))
        selected_str = selected.strftime('%Y-%m-%d')

        self.logger.info(
            f"Target expiration {target} → selected {selected_str} "
            f"from {len(expirations)} available"
        )
        return selected_str

    @staticmethod
    def _parse_option_symbol(symbol):
        """
        Parse OCC option symbol into (expiration, call_put, strike).

        Format: {TICKER}{YYMMDD}{C|P}{8-digit-strike*1000}
        Example: AAPL260620C00150000 → ('2026-06-20', 'C', 150.0)

        Returns None on parse failure (logged at DEBUG level by callers).
        """
        if not symbol:
            return None
        m = re.match(r'^([A-Z]+)(\d{6})([CP])(\d{8})$', symbol)
        if not m:
            return None
        _, date_str, opt_type, strike_str = m.groups()
        try:
            expiry = datetime.strptime(date_str, '%y%m%d').strftime('%Y-%m-%d')
            strike = int(strike_str) / 1000.0
        except ValueError:
            return None
        return expiry, opt_type, strike

    def _save_option_data(self, ticker, option_data_dict):
        """
        Save to CSV with the same 5-line metadata header as YahooFinanceDownloader,
        so load_option_data() can read it unchanged in Phase 2.
        """
        exp_date_str = option_data_dict['expiration_date'].replace('-', '')
        filename = f"{ticker}_{exp_date_str}_optionchain.csv"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, 'w') as f:
            f.write(f"Ticker,{ticker}\n")
            f.write(f"CurrentPrice,{option_data_dict['current_price']}\n")
            f.write(f"ExpirationDate,{option_data_dict['expiration_date']}\n")
            f.write(f"DownloadTimestamp,{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("\n")

        option_data_dict['option_data'].to_csv(filepath, mode='a', index=False)
        self.logger.debug(
            f"Saved {len(option_data_dict['option_data'])} strikes to {filepath}"
        )
        return filepath

    def _find_existing_file(self, ticker, expiration_date):
        """Return cached filepath if it exists, None otherwise."""
        if expiration_date.lower() in ('next_3fr_monthly', 'current_3fr_monthly'):
            return None
        exp_str  = expiration_date.replace('-', '')
        filepath = os.path.join(self.output_dir, f"{ticker}_{exp_str}_optionchain.csv")
        return filepath if os.path.exists(filepath) else None
