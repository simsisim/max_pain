#!/usr/bin/env python3
"""
Max Pain Calculator - Main Entry Point

Calculate max pain prices for stock options and generate reports.
"""

import sys
import os
import argparse
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils import load_config, setup_logging, get_data_source_config
from src.max_pain_calculator import MaxPainCalculator
from src.report_generator import ReportGenerator
from src.data_sources.factory import DataSourceFactory


def print_banner():
    """Print application banner"""
    print("=" * 60)
    print("MAX PAIN CALCULATOR v1.0")
    print("=" * 60)


def parse_arguments():
    """
    Parse command-line arguments

    Returns:
        Namespace with arguments
    """
    parser = argparse.ArgumentParser(
        description='Calculate max pain for stock options',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          # Use config.ini settings
  python main.py --ticker NVDA            # Override single ticker
  python main.py --ticker-choice 2        # Override ticker universe
  python main.py --data-file path/to/file.csv  # Use specific data file
        """
    )

    parser.add_argument('--ticker', help='Single ticker to analyze')
    parser.add_argument('--ticker-choice', type=int, help='Ticker universe choice (0-7)')
    parser.add_argument('--data-file', help='Path to CBOE CSV data file')
    parser.add_argument('--config', default='config.ini', help='Path to config file')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')

    return parser.parse_args()


def main():
    """Main execution function"""
    print_banner()

    # Parse arguments
    args = parse_arguments()

    try:
        # Load configuration
        config = load_config(args.config)
        print(f"Configuration: {args.config}")

        # Override log level if verbose
        if args.verbose:
            config.set('LOGGING', 'log_level', 'DEBUG')

        # Setup logging
        logger = setup_logging(config)
        logger.info("Starting Max Pain Calculator")

        # Initialize components
        calculator = MaxPainCalculator()
        report_generator = ReportGenerator(config)

        # Get data source configuration
        ds_config = get_data_source_config(config)
        data_source = ds_config['source']
        expiration_date = ds_config['expiration_date']
        
        # Create appropriate data adapter
        adapter = DataSourceFactory.create_adapter(
            data_source,
            ds_config['source_specific_config']
        )
        logger.info(f"Using {data_source} data source")

        # Determine tickers to process
        if args.ticker:
            tickers = [args.ticker]
        else:
            # Get ticker choice from config
            ticker_choice = args.ticker_choice if args.ticker_choice is not None else config.getint('TICKER_SELECTION', 'ticker_choice', fallback=7)

            if ticker_choice == 7:  # TEST mode - NVDA only
                tickers = ['NVDA']
            else:
                logger.error(f"Ticker choice {ticker_choice} not yet implemented")
                logger.error("Currently only supports ticker_choice=7 (TEST - NVDA)")
                sys.exit(1)

        # Display configuration
        print(f"Data Source: {data_source}")
        print(f"Ticker(s): {', '.join(tickers)}")
        print(f"Expiration Date: {expiration_date}")
        print()

        # Check if download-first mode is enabled for YF
        download_phase_enabled = config.getboolean('YAHOO_FINANCE', 'download_phase_enabled', fallback=False) if data_source == 'YF' else False
        
        # PHASE 1: Download all tickers (YF only, if enabled)
        filepaths = {}
        if data_source == 'YF' and download_phase_enabled:
            from src.data_sources.yf_downloader import YahooFinanceDownloader
            
            print("=" * 60)
            print("[PHASE 1] DOWNLOADING OPTION CHAIN DATA")
            print("=" * 60)
            
            downloader = YahooFinanceDownloader(ds_config['source_specific_config'])
            download_results = downloader.download_batch(tickers, expiration_date)
            
            print()
            print("Download Summary:")
            print(f"  ✓ Succeeded: {len(download_results['succeeded'])}/{len(tickers)}")
            if download_results['failed']:
                print(f"  ✗ Failed: {len(download_results['failed'])}/{len(tickers)}")
                for ticker, error in download_results['failed'].items():
                    print(f"    - {ticker}: {error}")
            
            # Continue only with successfully downloaded tickers
            tickers = download_results['succeeded']
            filepaths = download_results['filepaths']
            
            if not tickers:
                logger.error("No tickers successfully downloaded")
                sys.exit(1)
            
            print()
            print(f"Proceeding to process {len(tickers)} ticker(s)...")
            print()

        # PHASE 2: Process tickers
        print("=" * 60)
        phase_label = "[PHASE 2] CALCULATING MAX PAIN" if download_phase_enabled and data_source == 'YF' else "[INFO] PROCESSING"
        print(phase_label)
        print("=" * 60)
        print()
        
        results_list = []

        for i, ticker in enumerate(tickers, 1):
            try:
                print(f"[{i}/{len(tickers)}] Processing {ticker}...")

                # Get option data based on mode
                if data_source == 'YF' and download_phase_enabled:
                    # Load from previously downloaded CSV file
                    from src.data_sources.yf_downloader import YahooFinanceDownloader
                    downloader = YahooFinanceDownloader(ds_config['source_specific_config'])
                    option_data_dict = downloader.load_option_data(filepaths[ticker])
                else:
                    # Stream mode: fetch directly (CBOE or YF without download phase)
                    option_data_dict = adapter.fetch_option_data(ticker, expiration_date)
                
                # Calculate max pain
                result = calculator.calculate_max_pain(
                    option_data_dict['option_data'],
                    option_data_dict['current_price']
                )
                
                # Add ticker and expiration info
                result['ticker'] = option_data_dict['ticker']
                result['expiration_date'] = option_data_dict['expiration_date']
                
                # Preserve option_data for chart generation
                result['option_data'] = option_data_dict['option_data']

                # Display result
                print(f"  ├─ Ticker: {result['ticker']}")
                print(f"  ├─ Current Price: ${result['current_price']:.2f}")
                print(f"  ├─ Max Pain: ${result['max_pain_price']:.2f}")
                print(f"  ├─ Change: {result['pct_change']:+.2f}%")
                premium_bias = result['premium_bias'].upper()
                print(f"  ├─ Net Premium: ${result['net_call_put_premium']:,.2f} ({premium_bias} bias)")
                print(f"  └─ Status: ✓ Complete\n")

                results_list.append(result)

            except Exception as e:
                logger.error(f"Error processing {ticker}: {e}")
                print(f"  └─ Status: ✗ Failed - {e}\n")
                continue

        if not results_list:
            logger.error("No results to generate reports")
            sys.exit(1)

        # Generate charts (if enabled)
        if config.getboolean('OUTPUT', 'generate_charts', fallback=False):
            from src.chart_generator import MaxPainChartGenerator
            
            print()
            print("=" * 60)
            print("CHART GENERATION")
            print("=" * 60)
            
            chart_generator = MaxPainChartGenerator(config)
            
            for result in results_list:
                ticker = result.get('ticker', 'UNKNOWN')
                try:
                    chart_files = chart_generator.generate_charts(result)
                    if chart_files:
                        print(f"  ✓ {ticker}: Generated {len(chart_files)} chart(s)")
                        for chart_file in chart_files:
                            print(f"    - {os.path.basename(chart_file)}")
                    else:
                        print(f"  ⊗ {ticker}: No charts generated")
                except Exception as e:
                    logger.error(f"Error generating charts for {ticker}: {e}")
                    print(f"  ✗ {ticker}: Chart generation failed - {e}")
            
            print()

        # Generate reports
        print("=" * 60)
        print("REPORT GENERATION")
        print("=" * 60)
        start_time = datetime.now()

        # Remove option_data from results (not needed for reports, causes JSON serialization issues)
        for result in results_list:
            result.pop('option_data', None)

        generated_files = report_generator.generate_reports(results_list)

        for format_type, filepath in generated_files.items():
            format_label = format_type.upper()
            print(f"  ├─ {format_label}: {filepath}")

        print(f"  └─ Complete")

        # Summary
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\nCompleted in {elapsed:.1f} seconds")

        logger.info("Max Pain Calculator completed successfully")

    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
