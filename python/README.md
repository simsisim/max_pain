# Max Pain Calculator

Calculate the **max pain strike price** for a list of stock tickers at options expiration — the price where market makers would pay out the least total premium.

## Overview

**Max Pain Theory**: At expiration, the stock price tends to gravitate toward the strike where the combined payout to all option holders is minimized. This is where the largest number of options expire worthless.

This calculator:
- Downloads option chain data from Yahoo Finance (batch, with local caching)
- Calculates max pain prices using the standard payout minimization algorithm
- Generates professional reports in HTML, CSV, and JSON formats
- Supports single tickers or a full list from a CSV file

---

## Data Sources

| Source | Bulk list download | Single ticker | Notes |
|--------|-------------------|---------------|-------|
| **Yahoo Finance (YF)** | **Yes — recommended** | Yes | Free, reliable, cached locally |
| **CBOE** | No | Manual file only | Delayed 15–20 min, scraping fragile |

**Use YF for everything.** CBOE's download URL is a retail webpage button, not an API — it blocks bulk automated requests and its ToS prohibits scraping. Use `source = YF` in `config.ini`.

---

## Installation

```bash
# Navigate to project directory
cd /home/imagda/_invest2024/python/max_pain/python

# Install dependencies
pip install -r requirements.txt

# Verify
python main.py --help
```

**Requirements**: Python 3.9+, pandas, numpy, yfinance, jinja2, requests (see `requirements.txt`)

---

## Quick Start

### Single ticker
```bash
python main.py --ticker NVDA
```

### List of tickers from a CSV file
```bash
python main.py --ticker-file user_input/test.csv
```

### Use config.ini defaults (ticker_file + source defined there)
```bash
python main.py
```

---

## Ticker Input

Three ways to specify tickers, in order of priority:

| Method | How |
|--------|-----|
| CLI single ticker | `--ticker AAPL` |
| CLI ticker file | `--ticker-file user_input/test.csv` |
| Config file | `ticker_file = user_input/sp500_tickers.csv` in `config.ini` |

### CSV file format

Files live in `user_input/`. One column, header must be `ticker`:

```
ticker
BKNG
MELI
NFLX
META
COST
```

Pre-made lists available:
- `user_input/sp500_tickers.csv`
- `user_input/nasdaq100_tickers.csv`
- `user_input/russell3000_tickers.csv`
- `user_input/iwm1000_tickers.csv`
- `user_input/test.csv` (10 tickers for testing)

---

## How Downloads Work (YF 2-Phase Architecture)

With `download_phase_enabled = true` (default for YF), the program runs in two phases:

**Phase 1 — Download**
- Fetches option chain for each ticker from Yahoo Finance
- Saves one CSV file per ticker to `data/raw/yf/`
- Skips tickers where the file already exists (`overwrite_existing = false`)
- Rate-limited to avoid API bans (1 s between requests by default)

**Phase 2 — Calculate**
- Reads the locally saved CSV files
- Calculates max pain for each ticker
- Generates reports

### Downloaded file location

```
data/raw/yf/
├── BKNG_20260220_optionchain.csv
├── MELI_20260220_optionchain.csv
├── NFLX_20260220_optionchain.csv
└── ...
```

Filename format: `{TICKER}_{YYYYMMDD}_optionchain.csv`

On a second run with `overwrite_existing = false`, Phase 1 is instant — all files are reused.

---

## Expiration Date

Set in `config.ini`:

```ini
[CALCULATION]
# Options:
#   current_3Fr_monthly  = 3rd Friday of THIS month (auto-resolved)
#   next_3Fr_monthly     = 3rd Friday of NEXT month (advances past mid-month)
#   YYYY-MM-DD           = specific date e.g. 2026-03-20
expiration_date = current_3Fr_monthly
```

> **Note**: If today is expiration day itself, options have already settled. Use `next_3Fr_monthly` for a forward-looking run.

---

## Configuration

Full configuration is in `config.ini`. Key sections:

```ini
[DATA_SOURCE]
source = YF          # YF = Yahoo Finance (recommended). CBOE = manual file only.

[TICKER_SELECTION]
ticker_file = user_input/test.csv   # default ticker list

[YAHOO_FINANCE]
download_phase_enabled = true       # 2-phase download/process
download_dir = data/raw/yf          # where files are saved
overwrite_existing = false          # skip re-download if file exists
rate_limit_delay = 1                # seconds between requests

[OUTPUT]
output_formats = html,csv,json
sort_by = net_premium               # or: ticker, pct_change
highlight_top_n = 20

[LOGGING]
log_level = INFO
log_file = logs/max_pain.log
```

---

## Command-Line Options

```
python main.py [OPTIONS]

Options:
  --ticker TICKER        Single ticker to analyze
  --ticker-file FILE     CSV file with 'ticker' column
  --config FILE          Config file path (default: config.ini)
  --verbose              Enable DEBUG logging
  --help                 Show help
```

---

## Example Output

```
============================================================
MAX PAIN CALCULATOR v1.0
============================================================
Configuration: config.ini
Data Source: YF
Ticker(s): BKNG, MELI, REGN, CHTR, KLAC, META, ASML, NFLX, COST, ADBE
Expiration Date: 2026-02-20

============================================================
[PHASE 1] DOWNLOADING OPTION CHAIN DATA
============================================================
  [1/10] Downloading BKNG...
    ✓ Saved to BKNG_20260220_optionchain.csv
  [2/10] Downloading MELI...
    ↻ Using existing file
  ...

Download Summary:
  ✓ Succeeded: 10/10

============================================================
[PHASE 2] CALCULATING MAX PAIN
============================================================
[1/10] Processing BKNG...
  ├─ Ticker: BKNG
  ├─ Current Price: $4823.10
  ├─ Max Pain: $4700.00
  ├─ Change: -2.55%
  ├─ Net Premium: $8,420,000.00 (CALL bias)
  └─ Status: ✓ Complete
```

---

## Methodology

### Max Pain Calculation

For each candidate strike price X:

```
Call Payout(X) = Σ max(0, X - k) × Call_OI[k] × 100   for all strikes k
Put  Payout(X) = Σ max(0, k - X) × Put_OI[k]  × 100   for all strikes k
Total Payout(X) = Call Payout(X) + Put Payout(X)

Max Pain = strike X where Total Payout(X) is minimum
```

### Net Premium

```
Net Premium = ITM Call Premium - ITM Put Premium
  where ITM calls: k < Max Pain
        ITM puts:  k > Max Pain
```

- **Positive (CALL bias)**: more call premium at risk — downward pressure expected
- **Negative (PUT bias)**: more put premium at risk — upward pressure expected

---

## Project Structure

```
python/
├── main.py                          # Entry point
├── config.ini                       # Configuration
├── requirements.txt
├── README.md
│
├── src/
│   ├── utils.py                     # Config loading, date helpers
│   ├── max_pain_calculator.py       # Core calculation engine
│   ├── report_generator.py          # HTML/CSV/JSON output
│   ├── chart_generator.py           # Chart generation
│   └── data_sources/
│       ├── yf_adapter.py            # Yahoo Finance adapter
│       ├── yf_downloader.py         # YF batch downloader (Phase 1)
│       ├── cboe_adapter.py          # CBOE CSV file adapter
│       ├── cboe_downloader.py       # CBOE downloader (single ticker)
│       └── factory.py               # Adapter factory
│
├── user_input/                      # Ticker list CSV files
│   ├── test.csv                     # 10 tickers (testing)
│   ├── nasdaq100_tickers.csv
│   ├── sp500_tickers.csv
│   ├── russell3000_tickers.csv
│   └── iwm1000_tickers.csv
│
├── data/
│   └── raw/
│       ├── yf/                      # YF downloaded option chains
│       └── cboe/                    # CBOE CSV files (manual)
│
├── results/                         # Generated reports
│   ├── html/
│   ├── csv/
│   ├── json/
│   └── charts/
│
└── logs/
    └── max_pain.log
```

---

## Troubleshooting

**No data for a ticker**
YF may not have options data for all tickers (very small caps, some foreign listings). The ticker is skipped and logged — other tickers continue.

**Expiration date not found**
YF returns available expirations near the requested date. `yf_expiration_selection = nearest` picks the closest one automatically.

**Rate limit / download failures**
Increase `rate_limit_delay` in `[YAHOO_FINANCE]`. Default is 1 second.

**Re-download existing files**
Set `overwrite_existing = true` in `[YAHOO_FINANCE]` and re-run.

**Missing dependencies**
```bash
pip install --upgrade -r requirements.txt
```

---

## Disclaimer

Max pain is not a prediction and should not be used as the sole basis for trading decisions.

- Market makers hedge dynamically — pinning is not guaranteed
- Manipulation does not occur every cycle
- Use as one directional indicator among many
- Not financial advice — consult a licensed financial advisor before trading
- Past max pain levels do not guarantee future price behavior

---

**Version**: 1.1.0
**Last Updated**: 2026-02-20
