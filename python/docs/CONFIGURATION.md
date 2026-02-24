# Configuration Reference

All settings live in `python/config.ini`. No code changes are required to adjust behaviour — edit the INI file and re-run.

---

## [DATA_SOURCE]

```ini
[DATA_SOURCE]
source = YF
```

| Key | Values | Default | Notes |
|-----|--------|---------|-------|
| `source` | `YF`, `CBOE` | `YF` | Yahoo Finance is recommended. CBOE requires manual CSV placement. |

---

## [TICKER_SELECTION]

```ini
[TICKER_SELECTION]
ticker_file = user_input/nasdaq100_tickers.csv
```

| Key | Type | Notes |
|-----|------|-------|
| `ticker_file` | path | CSV with a `ticker` column header. Relative to project root or absolute. |

The CLI flags `--ticker` and `--ticker-file` override this setting. Priority order:

1. `--ticker AAPL` (CLI single)
2. `--ticker-file path/to/file.csv` (CLI file)
3. `ticker_file` in config (default)

---

## [CALCULATION]

### Expiration date

```ini
expiration_date = current_3Fr_monthly
```

| Value | Meaning |
|-------|---------|
| `current_3Fr_monthly` | 3rd Friday of the current calendar month |
| `next_3Fr_monthly` | 3rd Friday of next month; use if today is on or past mid-month |
| `YYYY-MM-DD` | Specific date, e.g. `2026-03-21` |

```ini
yf_expiration_selection = nearest
```

| Value | Meaning |
|-------|---------|
| `nearest` | Closest available YF expiration to the target date |
| `next_available` | First YF expiration on or after the target date |
| `exact` | Must match exactly; raises an error if not available |

### Price source

```ini
price_source = last_trade
```

| Value | Meaning |
|-------|---------|
| `last_trade` | Most recent trade price from YF info dict |
| `close` | Prior session close |

### Option types

```ini
option_types = both
```

| Value | Meaning |
|-------|---------|
| `both` | Include calls and puts (standard) |
| `calls_only` | Only call open interest |
| `puts_only` | Only put open interest |

---

### Mod 1 — Strike Band Filter

```ini
strike_band_pct = 15
```

Restricts the strike universe to those within ±N% of the current spot price before running the pain calculation.

**Why this matters:** Deep-OTM strikes often carry tiny (or erroneous) OI that can pull the pain minimum far from the real concentration zone. For example, a single high-OI strike at 10% of spot on a $900 stock would otherwise dominate the result.

| Value | Effect |
|-------|--------|
| `0` | Disabled — all strikes used |
| `15` | Keep strikes within $765–$1035 on a $900 stock |
| `20` | Wider band; useful for highly volatile tickers |
| `10` | Tighter band; best for stable, large-cap stocks |

Dropped strike count is logged at INFO level on each run.

---

### Mod 2 — Minimum OI Threshold

```ini
min_open_interest = 10
```

Drops strikes where `Call_OI + Put_OI < min_open_interest`. Applied after the band filter.

**Why this matters:** A single-contract strike (OI = 1) in an otherwise quiet band can still create a local minimum in the pain curve, producing a misleading result.

| Value | Effect |
|-------|--------|
| `0` | Disabled |
| `10` | Default — removes near-zero OI noise |
| `100` | Strict — useful for high-volume indices (SPX, QQQ) |

---

### Mod 3 — Dollar-Weighted OI

```ini
dollar_weighted_oi = false
```

When `true`, the pain formula uses `OI × Strike` instead of raw OI. This gives proportionally more influence to high-priced strikes, reflecting that a $5000 strike contract represents a larger notional position than a $50 strike contract.

**When to enable:** Large-cap stocks where strike prices span a wide dollar range (e.g. BKNG $3000–$6000).

| Value | Effect |
|-------|--------|
| `false` | Standard unweighted OI (default) |
| `true` | OI weighted by strike price |

---

### Mod 6 — Volume-Weighted OI

```ini
volume_weighted_oi = false
```

Substitutes today's traded volume (`Call_Volume` / `Put_Volume`) for open interest in the pain formula. OI accumulates over many sessions; volume tells you where contracts actually changed hands *today*.

**When to enable:**
- Mid-session runs where you want to weight by active flow, not historical accumulation
- Situations where a strike has large legacy OI but very little current-day activity (or vice versa)

**Fallback behaviour:**

| Situation | Behaviour |
|-----------|-----------|
| Volume columns missing (old CSV, CBOE source) | Falls back to OI; WARNING logged |
| Volume columns present but all-zero (pre-market) | Falls back to OI; WARNING logged |
| Volume available | Volume replaces OI for pain calculation |

**Composition with Mod 3:**

| Mod 3 | Mod 6 | Effective weighting |
|-------|-------|---------------------|
| off | off | `OI` (baseline) |
| on  | off | `OI × Strike` |
| off | on  | `Volume` |
| on  | on  | `Volume × Strike` (dollar-volume) |

Net premium and OI totals in the output always use the original unweighted OI regardless of this setting.

---

### Mod 4 — Smooth Pain Curve

```ini
smooth_pain_curve = false
smoothing_window = 3
```

Applies a centred rolling average of width `smoothing_window` to the total-payout curve before finding the minimum. Raw payout values are preserved in the output.

**When to enable:** When the pain curve is very jagged and the raw minimum sits in a one-strike notch rather than a broad trough.

| Key | Value | Effect |
|-----|-------|--------|
| `smooth_pain_curve` | `false` | No smoothing (default) |
| `smooth_pain_curve` | `true` | Enable rolling average |
| `smoothing_window` | `3` | 3-strike centred window (min useful) |
| `smoothing_window` | `5` | Wider smoothing |

---

## [OUTPUT]

```ini
[OUTPUT]
output_dir = results
output_formats = html,csv,json
generate_charts = true
chart_dir = results/charts
chart_dpi = 150
chart_width = 12
chart_height = 6
chart_types = total_payout,open_interest,gamma_overlay
sort_by = net_premium
highlight_top_n = 20
```

### output_formats

Comma-separated list of report formats to generate.

| Value | Output |
|-------|--------|
| `html` | Styled HTML table report |
| `csv` | Flat CSV for spreadsheet import |
| `json` | Full structured JSON with metadata |

### chart_types

Comma-separated list of chart types to generate per ticker. Set to `all` to enable every type.

| Chart type | Description | Requires |
|------------|-------------|----------|
| `total_payout` | Pain curve line chart | — |
| `open_interest` | Call/put OI bar chart | — |
| `pain_comparison` | Stacked call vs put pain | — |
| `gamma_overlay` | Payout curve + net gamma bars (twin axis) | YF gamma data |
| `all` | All of the above | — |

`gamma_overlay` is silently skipped (not an error) when gamma columns are absent from the downloaded data.

### sort_by

Controls the row order in the HTML and CSV reports.

| Value | Sort key |
|-------|----------|
| `net_premium` | Largest absolute net premium first |
| `ticker` | Alphabetical |
| `pct_change` | Largest absolute percentage change first |

### highlight_top_n

Highlights the top N rows (by sort key) in the HTML report. Set to `0` to disable.

---

## [YAHOO_FINANCE]

```ini
[YAHOO_FINANCE]
use_yfinance_library = true
download_phase_enabled = true
download_dir = data/raw/yf
overwrite_existing = false
cache_downloads = true
cache_dir = data/raw/yf
cache_expiry_minutes = 60
max_retries = 3
retry_delay_seconds = 2
rate_limit_delay = 1
```

| Key | Default | Notes |
|-----|---------|-------|
| `download_phase_enabled` | `true` | 2-phase mode: download all first, then process |
| `download_dir` | `data/raw/yf` | Where CSVs are stored |
| `overwrite_existing` | `false` | Set `true` to force re-download |
| `rate_limit_delay` | `1` | Seconds between requests in batch mode |
| `max_retries` | `3` | Per-ticker download retry count |
| `retry_delay_seconds` | `2` | Delay between retries |

---

## [CBOE]

```ini
[CBOE]
base_url = https://www.cboe.com/delayed_quotes/
data_dir = data/raw/cboe
rate_limit_delay = 2
request_timeout = 30
download_phase_enabled = true
overwrite_existing = false
```

CBOE is suitable for single-file workflows only. Place downloaded CSV files in `data_dir` manually before running.

---

## [LOGGING]

```ini
[LOGGING]
log_level = INFO
log_file = logs/max_pain.log
```

| Level | What is logged |
|-------|---------------|
| `DEBUG` | Strike-level details, filter counts, column parsing |
| `INFO` | Per-ticker progress, phase transitions, file paths |
| `WARNING` | Missing data, fallbacks |
| `ERROR` | Download/calculation failures |

Pass `--verbose` on the CLI to temporarily override to `DEBUG` without editing the config file.

---

## Recipes

### Fast re-run with same data

```ini
[YAHOO_FINANCE]
overwrite_existing = false   # keep existing CSVs
```

### Force fresh download for all tickers

```ini
[YAHOO_FINANCE]
overwrite_existing = true
```

### Next monthly expiration (after mid-month)

```ini
[CALCULATION]
expiration_date = next_3Fr_monthly
```

### Strict filters for large-cap, high-volume tickers

```ini
[CALCULATION]
strike_band_pct = 10
min_open_interest = 100
```

### Conservative mode — all enhancements off (original behaviour)

```ini
[CALCULATION]
strike_band_pct = 0
min_open_interest = 0
dollar_weighted_oi = false
smooth_pain_curve = false
```

### Full enhancement stack

```ini
[CALCULATION]
strike_band_pct = 15
min_open_interest = 10
dollar_weighted_oi = true
volume_weighted_oi = false   # enabling both gives Volume × Strike
smooth_pain_curve = true
smoothing_window = 3

[OUTPUT]
chart_types = total_payout,open_interest,gamma_overlay
```

---

## Downloaded CSV Schema

Each file in `data/raw/yf/` has a 4-line metadata header followed by a blank line and then the option chain as CSV:

```
Ticker,NVDA
CurrentPrice,135.72
ExpirationDate,2026-03-21
DownloadTimestamp,2026-02-24 09:15:00

Strike,Call_OI,Put_OI,Call_Gamma,Put_Gamma,Call_Volume,Put_Volume
120.0,5200,1800,0.0823,0.0412,420,95
125.0,8100,3400,0.1045,0.0631,880,310
...
```

`Call_Gamma` / `Put_Gamma` are present when Yahoo Finance returns gamma for that expiration.
`Call_Volume` / `Put_Volume` are present whenever Yahoo Finance returns volume (standard for all equity options).
All four optional columns round-trip correctly through the CSV on subsequent loads. Missing columns in older cached CSVs are handled gracefully — the relevant feature falls back automatically with a logged warning.
