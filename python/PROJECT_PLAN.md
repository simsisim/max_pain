# Max Pain Calculator Project - Comprehensive Implementation Plan

Based on my exploration of your documentation, reference projects, and requirements, here's the complete project plan:

---

## **PROJECT OVERVIEW**

**Goal**: Build a professional max pain calculator that:
- Downloads option chain data from CBOE or Yahoo Finance
- Calculates max pain prices for selected tickers
- Outputs results in PDF-style report and HTML visualization
- Starts with NVDA, then expands to multiple tickers

**Reference Data**:
- Sample CBOE data: `/home/imagda/_invest2024/python/max_pain/python/nvda_quotedata.csv`
- Report format: `/home/imagda/_invest2024/python/max_pain/docus/2511-max-pain-report.pdf`
- Config pattern: `/home/imagda/_invest2024/python/dashboards/html_sparkline/config.ini`

---

## **1. PROJECT STRUCTURE**

```
/home/imagda/_invest2024/python/max_pain/
├── config.ini                      # Main configuration file
├── main.py                         # Main orchestrator
├── requirements.txt                # Python dependencies
├── README.md                       # Project documentation
├── .gitignore                      # Git ignore file
│
├── src/                           # Source code modules
│   ├── __init__.py
│   ├── data_downloader.py         # Downloads option data from CBOE/YF
│   ├── ticker_manager.py          # Manages ticker lists (like html_sparkline)
│   ├── max_pain_calculator.py     # Core calculation engine
│   ├── report_generator.py        # Creates reports (HTML/CSV/PDF)
│   └── utils.py                   # Helper functions
│
├── data/                          # Data storage
│   ├── raw/                       # Raw downloaded option data
│   │   └── YYYY-MM-DD/           # Date-organized folders
│   │       └── {TICKER}_quotedata.csv
│   ├── processed/                 # Calculated max pain results
│   │   └── YYYY-MM-DD/
│   │       └── max_pain_results.json
│   └── tickers/                   # Ticker list files (like html_sparkline)
│       ├── sp500_tickers.csv
│       ├── nasdaq100_tickers.csv
│       ├── portfolio_tickers.csv
│       └── test_tickers.csv
│
├── results/                       # Output reports
│   ├── html/
│   │   └── YYYY-MM-DD_max_pain_report.html
│   ├── csv/
│   │   └── YYYY-MM-DD_max_pain_report.csv
│   └── pdf/                       # Future: PDF exports
│       └── YYYY-MM-DD_max_pain_report.pdf
│
├── templates/                     # HTML templates
│   └── max_pain_report.html      # Jinja2 template for HTML output
│
├── docus/                         # Documentation (existing)
│   └── [existing files]
│
└── tests/                         # Unit tests (future)
    ├── __init__.py
    ├── test_calculator.py
    ├── test_downloader.py
    └── test_data/
        └── sample_nvda_quotedata.csv
```

---

## **2. CONFIGURATION FILE (config.ini)**

**Location**: `/home/imagda/_invest2024/python/max_pain/config.ini`

**Structure**:
```ini
[DATA_SOURCE]
# Data source: CBOE or YF (Yahoo Finance)
source = CBOE
# Alternative: source = YF

[TICKER_SELECTION]
# Ticker universe choice (similar to html_sparkline)
# 0 = Custom list (from data/tickers/custom_tickers.csv)
# 1 = S&P 500
# 2 = NASDAQ 100
# 3 = DOW 30
# 4 = Russell 1000
# 5 = Portfolio (from data/tickers/portfolio_tickers.csv)
# 6 = Single ticker (specify in ticker_list below)
# 7 = TEST (NVDA only for initial testing)
ticker_choice = 7

# For ticker_choice = 6, specify tickers (comma-separated)
ticker_list = NVDA

# Local directory for ticker lists
local_tickers_dir = data/tickers

[CALCULATION]
# Expiration date to analyze (format: YYYY-MM-DD)
# If "next_monthly", automatically finds next monthly expiration
expiration_date = next_monthly

# Current price source: last_trade, close, or manual
price_source = last_trade

# Option types to include: both, calls_only, puts_only
option_types = both

[OUTPUT]
# Output directory for reports
output_dir = results

# Output formats (comma-separated): html, csv, json, pdf
output_formats = html,csv,json

# Sort results by: net_premium, ticker, pct_change
sort_by = net_premium

# Top N tickers to highlight (like asterisk in PDF report)
highlight_top_n = 20

[CBOE]
# CBOE-specific settings
base_url = https://www.cboe.com/delayed_quotes/
# Rate limiting (seconds between requests)
rate_limit_delay = 2
# Timeout for requests (seconds)
request_timeout = 30

[YAHOO_FINANCE]
# Yahoo Finance-specific settings
# (for future implementation)
use_yfinance_library = true
rate_limit_delay = 1

[LOGGING]
# Logging level: DEBUG, INFO, WARNING, ERROR
log_level = INFO
# Log file location
log_file = logs/max_pain.log
```

---

## **3. DATA FLOW ARCHITECTURE**

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INPUT                                │
│  (config.ini: ticker_choice=7, source=CBOE, expiration=next)    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MAIN.PY (Orchestrator)                        │
│  - Loads configuration                                           │
│  - Initializes logging                                           │
│  - Coordinates workflow                                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌─────────────┐  ┌──────────────┐  ┌─────────────┐
│   TICKER    │  │     DATA     │  │ MAX PAIN    │
│  MANAGER    │  │  DOWNLOADER  │  │ CALCULATOR  │
│             │  │              │  │             │
│ - Get list  │  │ - Download   │  │ - Parse OI  │
│ - Validate  │  │   from CBOE  │  │ - Calculate │
│ - Save      │  │ - Save raw   │  │ - Compute   │
│             │  │   CSV        │  │   premium   │
└─────────────┘  └──────────────┘  └─────────────┘
         │               │               │
         └───────────────┼───────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    REPORT GENERATOR                              │
│  - Load calculated results                                       │
│  - Format data for output                                        │
│  - Generate HTML (with template)                                 │
│  - Generate CSV                                                  │
│  - Generate JSON                                                 │
│  - Save to results/ directory                                    │
└─────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OUTPUT FILES                                  │
│  - results/html/2025-12-08_max_pain_report.html                 │
│  - results/csv/2025-12-08_max_pain_report.csv                   │
│  - results/json/2025-12-08_max_pain_results.json                │
└─────────────────────────────────────────────────────────────────┘
```

---

## **4. MODULE SPECIFICATIONS**

### **4.1 main.py**

**Purpose**: Orchestrate entire workflow

**Key Functions**:
- `main()` - Entry point
  - Parse command-line arguments (optional override of config)
  - Load configuration from config.ini
  - Initialize logging
  - Execute workflow steps
  - Handle errors gracefully

**Workflow Steps**:
1. Load config
2. Initialize TickerManager → get ticker list
3. For each ticker:
   - DataDownloader → download option data
   - MaxPainCalculator → calculate max pain
   - Store results
4. ReportGenerator → create output files
5. Log summary statistics

**Command-line Interface**:
```bash
python main.py                          # Use config.ini settings
python main.py --ticker NVDA            # Override ticker
python main.py --source YF              # Override data source
python main.py --ticker-choice 2        # Override ticker universe
python main.py --expiration 2025-12-19  # Override expiration date
```

---

### **4.2 src/ticker_manager.py**

**Purpose**: Manage ticker lists (similar to html_sparkline implementation)

**Key Classes**:
- `TickerManager`
  - `__init__(config)` - Initialize with config
  - `get_tickers()` - Return list based on ticker_choice
  - `_get_sp500_tickers()` - Scrape from Wikipedia
  - `_get_nasdaq100_tickers()` - Scrape from Wikipedia
  - `_get_dow30_tickers()` - Scrape from Wikipedia
  - `_load_custom_list(filename)` - Load from CSV
  - `validate_ticker(ticker)` - Check if ticker exists
  - `save_ticker_list(tickers, filename)` - Cache to CSV

**Data Sources**:
- S&P 500: Wikipedia scraping
- NASDAQ 100: Wikipedia scraping
- DOW 30: Hardcoded list
- Custom: CSV files in data/tickers/

---

### **4.3 src/data_downloader.py**

**Purpose**: Download option chain data from CBOE or Yahoo Finance

**Key Classes**:

**A. CBOEDownloader**
- `download_option_chain(ticker, expiration_date)`
  - Fetches from CBOE delayed quotes
  - Returns raw HTML/data
  - Implements rate limiting
  - Handles retries and errors

- `parse_cboe_data(raw_data)`
  - Parses HTML table to DataFrame
  - Extracts: Strike, Calls OI, Puts OI, Last, Bid, Ask
  - Returns structured DataFrame

- `save_to_csv(df, ticker, date)`
  - Saves to data/raw/YYYY-MM-DD/{TICKER}_quotedata.csv
  - Format matches nvda_quotedata.csv structure

**B. YahooFinanceDownloader** (Future implementation)
- Similar interface using yfinance library
- `download_option_chain(ticker, expiration_date)`
- `parse_yf_data(raw_data)`

**Data Format** (CSV output):
```
Expiration Date,Calls,Last Sale,Net,Bid,Ask,Volume,IV,Delta,Gamma,Open Interest,Strike,Puts,Last Sale,Net,Bid,Ask,Volume,IV,Delta,Gamma,Open Interest
Fri Dec 19 2025,NVDA251219C00010000,170.97,-0.505,168.8,170.3,7,0,0.9999,0,142,10.00,NVDA251219P00010000,0.01,0,0,0.01,0,4.2548,-0.0002,0,4772
```

---

### **4.4 src/max_pain_calculator.py**

**Purpose**: Core max pain calculation engine

**Key Classes**:

**MaxPainCalculator**

**Methodology** (from UserGuide PDF):
1. Load option chain data
2. Extract: Strike, Calls OI, Puts OI, Current Price
3. For each potential strike price:
   - Calculate call premium: Σ(max(0, current_price - strike) × call_OI)
   - Calculate put premium: Σ(max(0, strike - current_price) × put_OI)
   - Total payout = call_premium + put_premium
4. Max pain = strike with MINIMUM total payout
5. Calculate net call/put premium

**Key Methods**:
- `calculate_max_pain(option_chain_df, current_price)`
  - Returns: max_pain_price, total_payout, net_premium

- `calculate_pain_at_strike(strike, option_chain_df, current_price)`
  - Calculate total payout if price expires at given strike
  - Returns: total_call_payout, total_put_payout

- `compute_net_premium(option_chain_df, max_pain_price)`
  - Net Call Premium = Σ(Calls OI at ITM strikes × 100)
  - Net Put Premium = Σ(Puts OI at ITM strikes × 100)
  - Net = Call Premium - Put Premium
  - Returns: net_premium (positive = more calls, negative = more puts)

- `calculate_percentage_change(current_price, max_pain_price)`
  - Returns: ((max_pain - current) / current) × 100

**Output Structure** (per ticker):
```python
{
    "ticker": "NVDA",
    "current_price": 179.92,
    "max_pain_price": 172.90,
    "pct_change": -9.08,
    "net_call_put_premium": 1053215168.00,
    "total_call_oi": 1234567,
    "total_put_oi": 987654,
    "calculation_date": "2025-12-08",
    "expiration_date": "2025-12-19",
    "data_source": "CBOE"
}
```

---

### **4.5 src/report_generator.py**

**Purpose**: Generate output reports in multiple formats

**Key Classes**:

**ReportGenerator**

**Methods**:
- `generate_html_report(results_list)`
  - Load template from templates/max_pain_report.html
  - Use Jinja2 templating
  - Sort by net_premium or ticker
  - Highlight top 20 (asterisk marker)
  - Include metadata (generation date, disclaimer)
  - Save to results/html/

- `generate_csv_report(results_list)`
  - Create CSV with columns:
    - Ticker, Friday Close, Max Pain, % Change, Net Call/(Put) Premium
  - Sort by preference
  - Save to results/csv/

- `generate_json_report(results_list)`
  - Full structured data export
  - Include all calculation details
  - Save to results/json/

- `generate_pdf_report(results_list)` (Future)
  - Use reportlab or weasyprint
  - Match style of 2511-max-pain-report.pdf

**HTML Template Structure**:
```html
<!DOCTYPE html>
<html>
<head>
    <title>Max Pain Report - {{ report_date }}</title>
    <style>
        /* CSS styling matching PDF report aesthetic */
    </style>
</head>
<body>
    <h1>MAX PAIN REPORT</h1>
    <h2>{{ report_date }}</h2>

    <div class="disclaimer">
        <p>Max pain is not a guarantee...</p>
    </div>

    <h3>Sorted by Net Premium</h3>
    <table>
        <thead>
            <tr>
                <th>Ticker</th>
                <th>Friday Close</th>
                <th>Max Pain</th>
                <th>% Change</th>
                <th>Net Call/(Put) Premium</th>
            </tr>
        </thead>
        <tbody>
            {% for result in results %}
            <tr class="{% if result.is_top_20 %}highlight{% endif %}">
                <td>{{ result.ticker }}{% if result.is_top_20 %}*{% endif %}</td>
                <td>{{ result.current_price|format_price }}</td>
                <td>{{ result.max_pain_price|format_price }}</td>
                <td class="{{ result.pct_change|change_class }}">{{ result.pct_change|format_pct }}</td>
                <td>{{ result.net_premium|format_dollars }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <div class="footer">
        <p>Generated with Max Pain Calculator</p>
        <p>Data source: {{ data_source }}</p>
    </div>
</body>
</html>
```

---

### **4.6 src/utils.py**

**Purpose**: Helper functions and utilities

**Functions**:
- `setup_logging(config)` - Configure logging
- `get_next_monthly_expiration()` - Find next 3rd Friday
- `validate_date(date_string)` - Validate date formats
- `format_currency(value)` - Format numbers as currency
- `format_percentage(value)` - Format as percentage
- `create_directory_structure()` - Create data/results folders
- `load_config(config_file)` - Load and validate config.ini
- `retry_with_backoff(func, max_retries=3)` - Retry decorator for downloads

---

## **5. DATA SPECIFICATIONS**

### **5.1 Input Data Format (CBOE CSV)**

**File**: `data/raw/2025-12-08/NVDA_quotedata.csv`

**Structure** (from nvda_quotedata.csv):
```
Line 1: Company name, Last price, Change
Line 2: Date, Bid, Ask, Size, Volume
Line 3: Header row
Line 4+: Option data rows
```

**Key Columns**:
- Column K (index 10): Open Interest - Calls
- Column L (index 11): Strike
- Column V (index 21): Open Interest - Puts

### **5.2 Output Data Formats**

**A. JSON** (processed results):
```json
{
  "metadata": {
    "report_date": "2025-12-08",
    "generation_timestamp": "2025-12-08T10:30:00",
    "data_source": "CBOE",
    "expiration_date": "2025-12-19",
    "ticker_count": 1,
    "top_n_highlighted": 20
  },
  "results": [
    {
      "ticker": "NVDA",
      "current_price": 179.92,
      "max_pain_price": 172.90,
      "pct_change": -9.08,
      "net_call_put_premium": 1053215168.00,
      "premium_bias": "call",
      "total_call_oi": 1234567,
      "total_put_oi": 987654,
      "is_top_20": true,
      "indices": ["NASDAQ 100", "DOW 30"]
    }
  ],
  "summary": {
    "avg_pct_change": -9.08,
    "bullish_count": 0,
    "bearish_count": 1,
    "total_net_premium": 1053215168.00
  }
}
```

**B. CSV**:
```csv
Ticker,Friday Close,Max Pain,% Change,Net Call/(Put) Premium
NVDA,179.92,172.90,-9.08%,1053215168.00
```

---

## **6. CALCULATION METHODOLOGY DETAILS**

### **Max Pain Algorithm** (from UserGuide)

**Step 1**: Load option chain data
- Strike prices: K (list of all strikes)
- Call OI: C[k] for each strike k
- Put OI: P[k] for each strike k
- Current price: S

**Step 2**: Define payout function
For a given price point X:
```
Call Payout(X) = Σ max(0, X - k) × C[k] × 100  for all k
Put Payout(X) = Σ max(0, k - X) × P[k] × 100  for all k
Total Payout(X) = Call Payout(X) + Put Payout(X)
```

**Step 3**: Find minimum
```
Max Pain = argmin_X { Total Payout(X) }
where X ∈ [min(K), max(K)]
```

**Step 4**: Calculate net premium
```
Net Premium = Call Premium - Put Premium
where:
  Call Premium = Σ C[k] × 100  for k < Max Pain  (ITM calls)
  Put Premium = Σ P[k] × 100  for k > Max Pain  (ITM puts)
```

**Step 5**: Calculate percentage change
```
% Change = ((Max Pain - Current Price) / Current Price) × 100
```

**Interpretation**:
- Negative % Change → Downward pressure expected
- Positive % Change → Upward pressure expected
- Positive Net Premium → More call premium (bullish bias)
- Negative Net Premium → More put premium (bearish bias)

---

## **7. EXECUTION WORKFLOW**

### **Phase 1: Initial Setup (NVDA Only)**

**Goal**: Validate entire pipeline with single ticker

**Steps**:
1. Create project structure
2. Create config.ini with ticker_choice=7 (TEST - NVDA)
3. Implement all modules
4. Test with existing nvda_quotedata.csv
5. Validate calculations against PDF report (NVDA expected: Close=179.92, Max Pain=172.90)
6. Generate HTML and CSV outputs

**Success Criteria**:
- Successfully reads CBOE data
- Calculates max pain within ±$0.50 of expected value
- Generates HTML report matching PDF style
- CSV export works correctly

### **Phase 2: Data Download Integration**

**Goal**: Automate CBOE data retrieval

**Steps**:
1. Implement CBOEDownloader
2. Test with NVDA live data
3. Add rate limiting and error handling
4. Cache downloaded data
5. Add retry logic for failed downloads

**Success Criteria**:
- Successfully downloads current option data
- Handles network errors gracefully
- Respects rate limits
- Saves data in correct format

### **Phase 3: Multi-Ticker Expansion**

**Goal**: Support multiple tickers

**Steps**:
1. Implement TickerManager
2. Add support for ticker_choice options (1-7)
3. Test with small lists (5-10 tickers)
4. Add progress indicators
5. Implement parallel processing (optional)

**Success Criteria**:
- Processes 10 tickers successfully
- Generates combined report
- Handles missing data gracefully
- Performance: < 10 seconds per ticker

### **Phase 4: Enhanced Reporting**

**Goal**: Professional output formats

**Steps**:
1. Refine HTML template with CSS
2. Add sorting options
3. Add filtering (by net premium threshold)
4. Add visualization charts (optional):
   - Bar chart of top 20 by net premium
   - Distribution of % changes
5. Consider PDF export

**Success Criteria**:
- Report matches professional quality of reference PDF
- Multiple sort options work
- Charts render correctly (if implemented)

### **Phase 5: Yahoo Finance Integration**

**Goal**: Alternative data source

**Steps**:
1. Research yfinance library API
2. Implement YahooFinanceDownloader
3. Map YF data format to internal format
4. Add source selection in config
5. Test accuracy vs CBOE

**Success Criteria**:
- YF data downloads successfully
- Calculations match CBOE results within tolerance
- User can switch sources via config

---

## **8. DEPENDENCIES & REQUIREMENTS**

### **requirements.txt**

```
# Core dependencies
pandas>=2.0.0
numpy>=1.24.0
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0

# Configuration
configparser>=5.3.0

# Reporting
jinja2>=3.1.2

# Optional: Yahoo Finance
yfinance>=0.2.0

# Optional: PDF generation
reportlab>=4.0.0
# or weasyprint>=60.0

# Optional: Progress bars
tqdm>=4.66.0

# Optional: Parallel processing
concurrent-futures>=3.1.1

# Testing
pytest>=7.4.0
pytest-cov>=4.1.0
```

### **Python Version**
- Python 3.9 or higher recommended

---

## **9. README.md OUTLINE**

```markdown
# Max Pain Calculator

Professional options max pain calculator with CBOE and Yahoo Finance integration.

## Overview
Calculates the "max pain" strike price where market makers would pay out the least amount of premium at options expiration.

## Features
- Download option data from CBOE or Yahoo Finance
- Calculate max pain for single or multiple tickers
- Support for multiple ticker universes (S&P 500, NASDAQ 100, custom)
- Generate HTML, CSV, and JSON reports
- Configurable via config.ini

## Installation
[Instructions]

## Quick Start
[Basic usage examples]

## Configuration
[Explain config.ini options]

## Usage
[Detailed examples]

## Methodology
[Explain max pain calculation]

## Output Format
[Describe output files]

## Disclaimer
Max pain is not a guarantee. Use for informational purposes only.

## References
- CBOE: https://www.cboe.com
- Max Pain Theory: [link]
```

---

## **10. TESTING STRATEGY**

### **Unit Tests**

**test_calculator.py**:
- Test max pain calculation with known data
- Test edge cases (no ITM options, equal call/put OI)
- Test net premium calculation
- Validate against nvda_quotedata.csv expected results

**test_downloader.py**:
- Mock CBOE responses
- Test parsing logic
- Test error handling
- Test rate limiting

**test_ticker_manager.py**:
- Test ticker list loading
- Test validation
- Test caching

### **Integration Tests**

- End-to-end workflow with test data
- Multi-ticker processing
- Report generation

### **Test Data**

**tests/test_data/sample_nvda_quotedata.csv**:
- Copy of known-good NVDA data
- Expected output: Max Pain = 172.90, % Change = -9.08%

---

## **11. LOGGING & ERROR HANDLING**

### **Logging Strategy**

**Log Levels**:
- DEBUG: Data parsing details, calculation steps
- INFO: Download progress, ticker processing, report generation
- WARNING: Missing data, fallback to defaults
- ERROR: Download failures, calculation errors

**Log Format**:
```
2025-12-08 10:30:45 [INFO] main: Starting max pain calculation
2025-12-08 10:30:46 [INFO] ticker_manager: Loaded 1 ticker(s): NVDA
2025-12-08 10:30:47 [INFO] downloader: Downloading CBOE data for NVDA
2025-12-08 10:30:49 [INFO] calculator: Max pain for NVDA: 172.90
2025-12-08 10:30:50 [INFO] report_generator: Generated HTML report
2025-12-08 10:30:50 [INFO] main: Completed successfully
```

### **Error Handling**

**Common Errors**:
- Network failures → Retry with exponential backoff
- Invalid ticker → Skip and log warning
- Parsing errors → Save raw data for debugging
- Missing OI data → Skip ticker
- Rate limit exceeded → Wait and retry

---

## **12. FUTURE ENHANCEMENTS**

### **Phase 6+**: Advanced Features

1. **Historical Tracking**
   - Store max pain calculations over time
   - Track accuracy: did price move toward max pain?
   - Generate accuracy reports

2. **Alerts & Notifications**
   - Email alerts when max pain > X% from current
   - Webhook integration

3. **Advanced Analytics**
   - Greeks calculation (delta, gamma)
   - Put/Call ratio analysis
   - Volume vs OI analysis
   - Unusual activity detection

4. **Web Interface**
   - Flask/FastAPI web app
   - Interactive charts (Plotly/Chart.js)
   - Real-time updates

5. **Database Integration**
   - SQLite or PostgreSQL
   - Store historical data
   - Query and analysis

6. **API Endpoint**
   - REST API for external tools
   - JSON responses

---

## **13. IMPLEMENTATION PRIORITY**

### **Must Have (MVP)**
1. ✅ Project structure
2. ✅ config.ini
3. ✅ CBOE data parsing (use existing CSV initially)
4. ✅ Max pain calculator
5. ✅ HTML report generator
6. ✅ CSV export
7. ✅ Single ticker (NVDA) working end-to-end

### **Should Have**
8. CBOE data downloader
9. Ticker manager (multiple tickers)
10. Error handling & logging
11. JSON export
12. Top 20 highlighting

### **Nice to Have**
13. Yahoo Finance integration
14. PDF export
15. Progress bars
16. Parallel processing
17. Unit tests

### **Future**
18. Historical tracking
19. Web interface
20. Database integration

---

## **14. INITIAL DEVELOPMENT CHECKLIST**

### **Setup Phase**
- [ ] Create directory structure
- [ ] Initialize git repository
- [ ] Create .gitignore
- [ ] Create config.ini
- [ ] Create requirements.txt
- [ ] Create README.md skeleton

### **Core Development**
- [ ] Implement src/utils.py (logging, config loading)
- [ ] Implement src/max_pain_calculator.py
- [ ] Test calculator with nvda_quotedata.csv
- [ ] Implement src/report_generator.py (CSV first)
- [ ] Create HTML template
- [ ] Implement HTML report generation
- [ ] Test end-to-end with NVDA

### **Enhancement**
- [ ] Implement src/data_downloader.py (CBOE)
- [ ] Implement src/ticker_manager.py
- [ ] Add JSON export
- [ ] Add error handling
- [ ] Add logging throughout
- [ ] Test with 5-10 tickers

### **Finalization**
- [ ] Complete README.md
- [ ] Add usage examples
- [ ] Create sample config files
- [ ] Add disclaimers
- [ ] Final testing

---

## **15. EXPECTED OUTPUT EXAMPLE**

**Terminal Output**:
```
Max Pain Calculator v1.0
========================
Configuration: config.ini
Data Source: CBOE
Ticker Universe: TEST (NVDA)
Expiration Date: 2025-12-19

[INFO] Processing 1 ticker(s)...

[1/1] NVDA
  ├─ Current Price: $179.92
  ├─ Max Pain: $172.90
  ├─ Change: -9.08%
  ├─ Net Premium: $1,053,215,168.00 (CALL bias)
  └─ Status: ✓ Complete

Report Generation:
  ├─ HTML: results/html/2025-12-08_max_pain_report.html
  ├─ CSV:  results/csv/2025-12-08_max_pain_report.csv
  └─ JSON: results/json/2025-12-08_max_pain_results.json

Completed in 3.2 seconds
```

---

## **SUMMARY**

This plan provides a complete roadmap for building a professional max pain calculator that:

1. **Follows industry standards** (modular, configurable, testable)
2. **Matches your reference implementations** (html_sparkline patterns, PDF report output)
3. **Uses proven methodologies** (from UserGuide PDF)
4. **Scales from single ticker to full universes**
5. **Provides multiple output formats**
6. **Handles errors gracefully**
7. **Is maintainable and extensible**

The project can start simple (NVDA only with existing CSV) and progressively add features (downloads, multiple tickers, advanced reporting) without requiring major refactoring.

**Next Steps**: Once you approve this plan, I can begin implementation starting with the MVP (Must Have items).
