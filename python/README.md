# Max Pain Calculator

Professional options max pain calculator with CBOE data integration. Calculate the "max pain" strike price where market makers would pay out the least amount of premium at options expiration.

## Overview

**Max Pain Theory**: The strike price at which market makers would pay out the LEAST amount of in-the-money (ITM) call or put premium at options expiration. This represents the point where the most options holders experience losses.

This calculator:
- Parses CBOE option chain data
- Calculates max pain prices using optimization algorithms
- Generates professional reports in HTML, CSV, and JSON formats
- Provides net premium analysis (call vs put bias)

## Features

✓ **CBOE Data Parsing** - Load and parse CBOE delayed quotes CSV format
✓ **Max Pain Calculation** - Find the strike with minimum total payout
✓ **Net Premium Analysis** - Calculate call vs put premium bias
✓ **Multiple Output Formats** - HTML, CSV, and JSON reports
✓ **Professional Reporting** - Beautiful HTML reports with statistics
✓ **Configurable** - Full configuration via config.ini
✓ **Logging** - Comprehensive logging for debugging

## Installation

### Requirements

- Python 3.9 or higher
- pandas, numpy, jinja2 (see requirements.txt)

### Setup

```bash
# Clone or navigate to the project directory
cd /home/imagda/_invest2024/python/max_pain

# Install dependencies
pip install -r requirements.txt

# Verify installation
python main.py --help
```

## Quick Start

### Basic Usage

```bash
# Run with default config (NVDA test data)
python main.py

# Use custom data file
python main.py --data-file python/nvda_quotedata.csv

# Enable verbose logging
python main.py --verbose
```

### Example Output

```
============================================================
MAX PAIN CALCULATOR v1.0
============================================================
Configuration: config.ini
Data Source: CBOE
Ticker Universe: TEST (NVDA)
Expiration Date: next_monthly

[INFO] Processing 1 ticker(s)...

[1/1] Processing nvda_quotedata.csv...
  ├─ Ticker: NVIDIA
  ├─ Current Price: $179.92
  ├─ Max Pain: $144.00
  ├─ Change: -19.96%
  ├─ Net Premium: $111,600.00 (CALL bias)
  └─ Status: ✓ Complete

Report Generation:
  ├─ CSV: results/csv/2025-12-08_max_pain_report.csv
  ├─ JSON: results/json/2025-12-08_max_pain_results.json
  ├─ HTML: results/html/2025-12-08_max_pain_report.html
  └─ Complete

Completed in 5.2 seconds
```

## Configuration

Edit `config.ini` to customize behavior:

### Data Source
```ini
[DATA_SOURCE]
source = CBOE  # or YF (Yahoo Finance - future)
```

### Ticker Selection
```ini
[TICKER_SELECTION]
ticker_choice = 7  # 0-7 (see options below)
# 0 = Custom list
# 1 = S&P 500
# 2 = NASDAQ 100
# 3 = DOW 30
# 4 = Russell 1000
# 5 = Portfolio
# 6 = Single ticker
# 7 = TEST (NVDA only)
```

### Output Options
```ini
[OUTPUT]
output_formats = html,csv,json
sort_by = net_premium  # or ticker, pct_change
highlight_top_n = 20
```

### Logging
```ini
[LOGGING]
log_level = INFO  # DEBUG, INFO, WARNING, ERROR
log_file = logs/max_pain.log
```

## Methodology

### Max Pain Calculation

The calculator uses the following algorithm:

**Step 1**: Load option chain data
- Strike prices (K)
- Call Open Interest (C[k])
- Put Open Interest (P[k])
- Current stock price (S)

**Step 2**: Calculate payout at each strike
For each potential price point X:
```
Call Payout(X) = Σ max(0, X - k) × C[k] × 100  for all k
Put Payout(X) = Σ max(0, k - X) × P[k] × 100  for all k
Total Payout(X) = Call Payout(X) + Put Payout(X)
```

**Step 3**: Find minimum
```
Max Pain = argmin { Total Payout(X) } for all strikes X
```

**Step 4**: Calculate net premium
```
Net Premium = Call Premium - Put Premium
where:
  Call Premium = Σ C[k] × 100  for k < Max Pain (ITM calls)
  Put Premium = Σ P[k] × 100  for k > Max Pain (ITM puts)
```

### Interpretation

- **Negative % Change**: Downward pressure (max pain < current price)
- **Positive % Change**: Upward pressure (max pain > current price)
- **Positive Net Premium**: More call premium (bullish bias)
- **Negative Net Premium**: More put premium (bearish bias)

## Output Formats

### CSV Report
```csv
Ticker,Friday Close,Max Pain,% Change,Net Call/(Put) Premium
NVIDIA,179.92,144.00,-19.96%,"111,600.00"
```

### JSON Report
```json
{
  "metadata": {
    "report_date": "2025-12-08",
    "data_source": "CBOE",
    "ticker_count": 1
  },
  "results": [
    {
      "ticker": "NVIDIA",
      "current_price": 179.92,
      "max_pain_price": 144.00,
      "pct_change": -19.96,
      "net_call_put_premium": 111600.00,
      "premium_bias": "call"
    }
  ]
}
```

### HTML Report

Beautiful, professional HTML report with:
- Summary statistics
- Color-coded percentage changes
- Sortable data
- Top 20 highlighting
- Print-friendly styling

View the HTML report in any web browser.

## Project Structure

```
max_pain/
├── main.py                     # Main entry point
├── config.ini                  # Configuration
├── requirements.txt            # Dependencies
├── README.md                   # This file
│
├── src/                        # Source code
│   ├── utils.py                # Utility functions
│   ├── max_pain_calculator.py  # Core calculation engine
│   └── report_generator.py     # Report generation
│
├── templates/                  # HTML templates
│   └── max_pain_report.html
│
├── data/                       # Data storage
│   ├── raw/                    # Raw option data
│   └── tickers/                # Ticker lists
│
├── results/                    # Generated reports
│   ├── html/
│   ├── csv/
│   └── json/
│
└── logs/                       # Log files
```

## Command-Line Options

```bash
python main.py [OPTIONS]

Options:
  --ticker TICKER          Single ticker to analyze
  --ticker-choice N        Ticker universe choice (0-7)
  --data-file FILE         Path to CBOE CSV data file
  --config FILE            Path to config file (default: config.ini)
  --verbose                Enable verbose logging
  --help                   Show help message
```

## Data Format

### CBOE CSV Format

The calculator expects CBOE delayed quotes CSV format:

```
Line 1: (empty)
Line 2: Company Name, Last: PRICE, Change: CHANGE
Line 3: Date info, Bid, Ask, Volume
Line 4: Headers (Expiration Date, Calls, Strike, OI, Puts, OI, etc.)
Line 5+: Option data rows
```

### Required Columns

- Strike
- Open Interest (for calls)
- Open Interest.1 (for puts)

## Examples

### Example 1: Single Ticker
```bash
python main.py --data-file python/nvda_quotedata.csv
```

### Example 2: Custom Config
```bash
python main.py --config my_config.ini
```

### Example 3: Verbose Mode
```bash
python main.py --verbose
```

## Troubleshooting

### CSV Parsing Errors
- Ensure CSV is in CBOE format
- Check for empty or corrupt files
- Verify column structure

### Missing Dependencies
```bash
pip install --upgrade -r requirements.txt
```

### Permission Errors
```bash
chmod +x main.py
```

## Disclaimer

**IMPORTANT**: Max pain is not a guarantee and should be used solely for directional clues. This tool is provided for educational and informational purposes only.

- Market makers can protect themselves by buying/selling underlying stock
- Manipulation does not occur every month
- Should be used as ONE indicator among many
- Not financial advice - consult a financial advisor before trading
- All data comes from CBOE - accuracy is not guaranteed
- Past performance does not guarantee future results

## Future Enhancements

### Phase 2 (Planned)
- [ ] CBOE data downloader (automated fetching)
- [ ] Multi-ticker batch processing
- [ ] Yahoo Finance integration
- [ ] Historical tracking

### Phase 3 (Future)
- [ ] Web interface
- [ ] Real-time updates
- [ ] Advanced analytics (Greeks, PCR)
- [ ] Database integration
- [ ] PDF export

## References

- **CBOE**: https://www.cboe.com/delayed_quotes/
- **Max Pain Theory**: Market maker behavior at options expiration
- **Project Documentation**: See PROJECT_PLAN.md for detailed specifications

## License

For internal use only.

## Support

For issues or questions, see the project documentation or review the logs in `logs/max_pain.log`.

---

**Version**: 1.0.0
**Last Updated**: 2025-12-08
**Author**: Max Pain Calculator Project
