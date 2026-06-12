# Max Pain Calculator

Calculate the **max pain strike price** for a list of stock tickers at options expiration — the price where market makers would pay out the least total premium.

---

## What is Max Pain?

**Max Pain Theory**: At expiration, the stock price tends to gravitate toward the strike where the combined payout to option sellers is minimized — i.e., the largest number of options expire worthless.

This tool:
- Downloads option chain data from Yahoo Finance (batch, with local caching)
- Calculates max pain using a robust, configurable payout-minimization algorithm
- Applies configurable filters and weighting to improve result reliability
- Generates reports in HTML, CSV, and JSON
- Generates PNG charts (payout curve, OI distribution, net gamma overlay)

---

## Quick Start

```bash
cd /home/imagda/_invest2024/python/max_pain/python

pip install -r requirements.txt

# Single ticker
python main.py --ticker NVDA

# Ticker list from CSV or plain/TradingView .txt
python main.py --ticker-file user_input/test.csv

# Use config.ini defaults
python main.py
```

---

## Data Source

Three sources are available, set via `source` in `[DATA_SOURCE]` of `config.ini`:

| Source | When to use | Notes |
|--------|-------------|-------|
| `YF` | Scheduled runs, market hours, right after close | Free, full option chain incl. gamma. Default. |
| `CBOE_JSON` | After-hours / pre-market manual runs | CBOE public JSON API — always returns the last EOD snapshot (published ~15:45 ET) regardless of time of day. Solves the YF zero-OI problem overnight. |
| `CBOE` | Single-file manual workflows only | CSV download endpoint blocks bulk automated requests. Not used in GitHub Actions. |

**Why CBOE_JSON for after-hours?** Yahoo Finance treats options data as live quotes. Outside market hours it returns OI = 0 for far-out expirations — filters then eliminate all strikes and every ticker fails. The CBOE delayed-quotes JSON API (`cdn.cboe.com/api/global/delayed_quotes/options/{TICKER}.json`) is a cached EOD snapshot that is available 24/7.

---

## Ticker Input

Three ways to specify tickers, in priority order:

| Method | How |
|--------|-----|
| CLI — single | `--ticker AAPL` |
| CLI — file | `--ticker-file user_input/test.csv` (or `.txt`) |
| Config default | `ticker_file = user_input/nasdaq100_tickers.csv` in `config.ini` |

Two file formats are supported, auto-detected by content:

**Plain `.txt`** — one ticker per line, no header:

```
BKNG
NFLX
META
NVDA
```

**TradingView watchlist `.txt`** — paste a watchlist export directly (comma-separated `EXCHANGE:TICKER` tokens). Section labels (`###...`) and unsupported instruments are filtered out automatically:

```
###MAG7,NASDAQ:GOOGL,NASDAQ:NVDA,NASDAQ:TSLA,###SEMIS,NASDAQ:AMAT,NASDAQ:LRCX
```

Filtered out automatically: indices (`TVC`, `DJ`), futures (`COMEX`, `!`-suffix), crypto (`CRYPTO`), and non-US exchanges (`TSE`, `KRX`, `LSE`, `NSE`, `TWSE`, `EURONEXT`, `GETTEX`, `OTC`). Skipped tokens are logged at startup.

**CSV** — one column, header must be `ticker`:

```
ticker
BKNG
NFLX
META
NVDA
```

Pre-made lists in `user_input/`:

| File | Contents |
|------|----------|
| `test.csv` | 10 tickers (testing) |
| `nasdaq100_tickers.csv` | NASDAQ 100 |
| `sp500_tickers.csv` | S&P 500 |
| `russell3000_tickers.csv` | Russell 3000 |
| `iwm1000_tickers.csv` | IWM constituents |
| `Ioa_port.txt` | Personal watchlist (TradingView export) |

---

## How Downloads Work (2-Phase Architecture)

With `download_phase_enabled = true` (default):

**Phase 1 — Download**
- Fetches option chain per ticker from Yahoo Finance
- Saves one CSV to `data/raw/yf/` per ticker
- Skips existing files when `overwrite_existing = false`
- Rate-limited (configurable)

**Phase 2 — Calculate**
- Reads saved CSVs
- Applies filters and enhancements
- Calculates max pain
- Generates reports and charts

On a second run, Phase 1 is near-instant — all files are reused.

---

## GitHub Actions — Automated Schedule

The workflow (`.github/workflows/max_pain.yml`) runs in two modes:

### Scheduled (automatic)

Triggers **every 2nd Friday of the month at 21:30 UTC (5:30 PM ET)** — one week before the monthly options expiration (3rd Friday). This gives you a full week of signal before expiration.

Runs **four ticker lists in parallel** (matrix), all targeting `next_3Fr_monthly`:
- `nasdaq100_tickers.csv`
- `sp500_tickers.csv`
- `iwm1000_tickers.csv`
- `Ioa_port.txt`

Uses **YF** data source (runs right after close — OI data is still valid at 5:30 PM ET).

Results and logs are uploaded as GitHub Actions artifacts, retained for 30 days.

### Manual dispatch

Go to **Actions → Max Pain Calculator → Run workflow** to trigger on demand. Options:

| Input | Default | Notes |
|-------|---------|-------|
| Ticker file | `test.csv` | Any file from the dropdown (CSV or `.txt`) |
| Expiration date | `next_3Fr_monthly` | Keyword or `YYYY-MM-DD` |
| Strike band % | `15` | Set to `0` to disable |
| Min open interest | `10` | Set to `0` to disable |
| Volume-weighted OI | `false` | Use today's volume instead of OI |
| Data source | `YF` | Use `CBOE_JSON` for after-hours runs (avoids YF zero-OI problem) |

### Artifacts

Each run uploads two artifacts named `max-pain-results-<run_id>-<index>` and `max-pain-logs-<run_id>-<index>`. On scheduled runs there are two sets (one per ticker file). Both are retained for **30 days**.

---

## Expiration Date

Set in `config.ini`:

```ini
[CALCULATION]
expiration_date = current_3Fr_monthly   # 3rd Friday of this month
# expiration_date = next_3Fr_monthly    # 3rd Friday of next month
# expiration_date = 2026-03-21          # specific date
```

If today is expiration day, use `next_3Fr_monthly` for a forward-looking run.

---

## Calculation Enhancements

Five configurable enhancements improve result reliability over the baseline algorithm. All default to safe values — the original behaviour is preserved when each is disabled.

### Mod 1 — Strike Band Filter *(critical fix)*

Restricts the analysis to strikes within ±N% of the current spot price. Eliminates deep-OTM strikes with tiny OI that can pull the pain minimum far from spot (e.g. the NFLX $85 result on a $900 stock).

```ini
strike_band_pct = 15    # ±15% around spot. Set to 0 to disable.
```

### Mod 2 — Minimum OI Threshold *(critical fix)*

Drops strikes where `Call_OI + Put_OI` is below a minimum. Prevents single-contract outliers from creating noise spikes.

```ini
min_open_interest = 10  # Set to 0 to disable.
```

### Mod 3 — Dollar-Weighted OI

Weights each strike's OI by its dollar notional (`OI × Strike`), giving proportionally more influence to high-priced strikes.

```ini
dollar_weighted_oi = false
```

### Mod 4 — Smooth Pain Curve

Applies a centred rolling average to the pain values before finding the minimum, reducing sensitivity to jagged strikes.

```ini
smooth_pain_curve = false
smoothing_window = 3
```

### Mod 6 — Volume-Weighted OI

Substitutes today's traded **volume** for open interest in the pain formula. Volume reveals where active money moved *today*, whereas OI reflects positions accumulated over time. Useful mid-session when a strike suddenly attracts heavy trading that hasn't yet shown up as a large OI change.

```ini
volume_weighted_oi = false
```

- Falls back silently to OI if volume data is absent or all-zero (pre-market runs, or older cached CSVs)
- Composes with `dollar_weighted_oi`: enabling both gives `Volume × Strike` (dollar-volume weighting)
- Requires YF data source (volume is captured alongside OI automatically)

---

### Mod 5 — Net Gamma Overlay (chart)

Captures `gamma` from Yahoo Finance and computes net gamma per strike:

```
Net Gamma = Call_OI × Call_Gamma − Put_OI × Put_Gamma
```

Positive = call-dominated (upward dealer hedging pressure).
Negative = put-dominated (downward pressure).

Shown as a bar chart overlaid on the payout curve. Does **not** change the max pain formula.

```ini
chart_types = total_payout,open_interest,gamma_overlay
```

---

## Methodology

### Max Pain Formula

For each candidate strike X:

```
Call Payout(X) = Σ max(0, X − k) × Call_OI[k] × 100   for all strikes k
Put  Payout(X) = Σ max(0, k − X) × Put_OI[k]  × 100   for all strikes k
Total Payout(X) = Call Payout(X) + Put Payout(X)

Max Pain = X  where  Total Payout(X) is minimum
```

With **Mod 3** active, `OI` is replaced by `OI × Strike` in the formula.
With **Mod 4** active, `Total Payout` is smoothed by a rolling mean before `argmin`.

### Net Premium

```
Net Premium = Σ Call_OI[k] × 100  (k < Max Pain)
            − Σ Put_OI[k]  × 100  (k > Max Pain)
```

- Positive (CALL bias) → more call premium at risk → mild downward gravity
- Negative (PUT bias)  → more put premium at risk → mild upward gravity

---

## Charts

| Chart type | File suffix | What it shows |
|------------|-------------|---------------|
| `total_payout` | `_total_payout.png` | Pain curve + current price + max pain |
| `open_interest` | `_open_interest.png` | Call / put OI bars per strike |
| `pain_comparison` | `_pain_comparison.png` | Stacked call vs put pain contribution |
| `gamma_overlay` | `_gamma_overlay.png` | Payout curve (left axis) + net gamma bars (right axis) |

Enable in `config.ini`:

```ini
generate_charts = true
chart_types = total_payout,open_interest,gamma_overlay
```

`gamma_overlay` is silently skipped when gamma data is not available (e.g. CBOE source).

---

## Command-Line Reference

```
python main.py [OPTIONS]

  --ticker TICKER       Single ticker to analyze
  --ticker-file FILE    CSV file with 'ticker' column
  --config FILE         Config file (default: config.ini)
  --verbose             Enable DEBUG logging
  --help                Show help message
```

---

## Example Run

```
============================================================
MAX PAIN CALCULATOR v1.2
============================================================
Configuration: config.ini
Data Source: YF
Ticker(s): BKNG, NFLX, META, NVDA
Expiration Date: 2026-03-21

============================================================
[PHASE 1] DOWNLOADING OPTION CHAIN DATA
============================================================
  [1/4] Downloading BKNG...
    ✓ Saved to BKNG_20260321_optionchain.csv
  [2/4] Downloading NFLX...
    ↻ Using existing file
  ...

Download Summary:
  ✓ Succeeded: 4/4

============================================================
[PHASE 2] CALCULATING MAX PAIN
============================================================
[1/4] Processing BKNG...
  ├─ Ticker: BKNG
  ├─ Current Price: $4823.10
  ├─ Max Pain: $4750.00
  ├─ Change: -1.51%
  ├─ Net Premium: $8,420,000.00 (CALL bias)
  └─ Status: ✓ Complete
```

---

## Project Structure

```
python/
├── main.py                          # Entry point and orchestrator
├── config.ini                       # All runtime settings
├── requirements.txt
├── README.md
├── docs/
│   └── CONFIGURATION.md             # Full config reference
│
├── src/
│   ├── utils.py                     # Config loading, date helpers
│   ├── max_pain_calculator.py       # Core calculation engine
│   ├── report_generator.py          # HTML / CSV / JSON output
│   ├── chart_generator.py           # PNG chart generation
│   └── data_sources/
│       ├── yf_adapter.py            # Yahoo Finance option chain adapter
│       ├── yf_downloader.py         # YF batch downloader (Phase 1)
│       ├── cboe_adapter.py          # CBOE CSV file adapter
│       ├── cboe_downloader.py       # CBOE single-file downloader
│       ├── cboe_json_downloader.py  # CBOE JSON API downloader (after-hours)
│       └── factory.py               # Adapter factory
│
├── user_input/                      # Ticker CSV files (tracked by git)
│   ├── test.csv
│   ├── nasdaq100_tickers.csv
│   ├── sp500_tickers.csv
│   ├── russell3000_tickers.csv
│   └── iwm1000_tickers.csv
│
├── data/
│   └── raw/
│       └── yf/                      # Downloaded option chain CSVs
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

**Max pain is far from the stock price (e.g. NFLX $85 on a $900 stock)**
Enable Mod 1 (strike band filter). Default `strike_band_pct = 15` already handles this — verify config was applied.

**No data for a ticker**
Yahoo Finance may not have options for very small caps or some foreign listings. The ticker is skipped; all others continue.

**Expiration date not found**
`yf_expiration_selection = nearest` picks the closest available date automatically.

**Download failures / rate limits**
Increase `rate_limit_delay` under `[YAHOO_FINANCE]` (default: 1 s).

**Re-download existing files**
Set `overwrite_existing = true` under `[YAHOO_FINANCE]` and re-run.

**All tickers fail with "No option data remaining after filters" (after-hours run)**
Yahoo Finance returns OI = 0 outside market hours for far-out expirations — the min OI filter then eliminates everything. Use `CBOE_JSON` as the data source in the manual dispatch dropdown. CBOE serves a valid EOD snapshot 24/7.

**Gamma overlay chart not generated**
The ticker's option chain must have a `gamma` column in Yahoo Finance's response. This is normally available for standard equity options. Check that `source = YF` and `generate_charts = true`.

**Missing dependencies**
```bash
pip install --upgrade -r requirements.txt
```

---

## Disclaimer

Max pain is a directional indicator, not a guarantee.

- Dealer pinning is a tendency, not a rule
- Use as one signal among many
- Past max pain levels do not predict future price behaviour
- Not financial advice — consult a licensed advisor before trading

---

**Version**: 1.3.0
**Last Updated**: 2026-06-12


