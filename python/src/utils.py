"""
Utility functions for Max Pain Calculator
"""

import logging
import configparser
import os
from datetime import datetime, timedelta
from pathlib import Path


def setup_logging(config):
    """
    Setup logging configuration

    Args:
        config: ConfigParser object with logging settings
    """
    log_level = config.get('LOGGING', 'log_level', fallback='INFO')
    log_file = config.get('LOGGING', 'log_file', fallback='logs/max_pain.log')

    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger('max_pain')


def load_config(config_file='config.ini'):
    """
    Load configuration from file

    Args:
        config_file: Path to config file

    Returns:
        ConfigParser object
    """
    config = configparser.ConfigParser()

    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    config.read(config_file)
    return config


def get_next_monthly_expiration(reference_date=None):
    """
    Find the next monthly options expiration (3rd Friday of the month)

    Args:
        reference_date: Starting date (defaults to today)

    Returns:
        datetime object for next expiration
    """
    if reference_date is None:
        reference_date = datetime.now()

    # Start with first day of next month
    if reference_date.day >= 15:  # If past mid-month, go to next month
        if reference_date.month == 12:
            year = reference_date.year + 1
            month = 1
        else:
            year = reference_date.year
            month = reference_date.month + 1
    else:
        year = reference_date.year
        month = reference_date.month

    # Find first day of the month
    first_day = datetime(year, month, 1)

    # Find first Friday (weekday 4)
    days_until_friday = (4 - first_day.weekday()) % 7
    first_friday = first_day + timedelta(days=days_until_friday)

    # Third Friday is 14 days after first Friday
    third_friday = first_friday + timedelta(days=14)

    return third_friday


def validate_date(date_string):
    """
    Validate date format (YYYY-MM-DD)

    Args:
        date_string: Date string to validate

    Returns:
        datetime object if valid, None otherwise
    """
    try:
        return datetime.strptime(date_string, '%Y-%m-%d')
    except ValueError:
        return None


def format_currency(value):
    """
    Format number as currency

    Args:
        value: Numeric value

    Returns:
        Formatted string
    """
    if value >= 1_000_000_000:
        return f"${value/1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"${value/1_000_000:.2f}M"
    elif value >= 1_000:
        return f"${value/1_000:.2f}K"
    else:
        return f"${value:.2f}"


def format_large_number(value):
    """
    Format large number with commas

    Args:
        value: Numeric value

    Returns:
        Formatted string
    """
    return f"{value:,.2f}"


def format_percentage(value):
    """
    Format number as percentage

    Args:
        value: Numeric value (e.g., -9.08 for -9.08%)

    Returns:
        Formatted string
    """
    return f"{value:+.2f}%"


def create_directory_structure(base_dir='.'):
    """
    Create necessary directory structure

    Args:
        base_dir: Base directory path
    """
    directories = [
        'src',
        'data/raw',
        'data/processed',
        'data/tickers',
        'results/html',
        'results/csv',
        'results/json',
        'templates',
        'logs',
        'tests/test_data'
    ]

    for directory in directories:
        path = os.path.join(base_dir, directory)
        os.makedirs(path, exist_ok=True)


def get_output_filename(prefix, extension, output_dir, include_date=True):
    """
    Generate output filename with timestamp

    Args:
        prefix: Filename prefix (e.g., 'max_pain_report')
        extension: File extension (e.g., 'html', 'csv')
        output_dir: Output directory
        include_date: Whether to include date in filename

    Returns:
        Full file path
    """
    if include_date:
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = f"{date_str}_{prefix}.{extension}"
    else:
        filename = f"{prefix}.{extension}"

    return os.path.join(output_dir, filename)


def safe_float(value, default=0.0):
    """
    Safely convert value to float

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Float value
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default=0):
    """
    Safely convert value to int

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Int value
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def get_expiration_date_from_config(config):
    """
    Get expiration date from config, handling various formats
    
    Args:
        config: ConfigParser object
    
    Returns:
        tuple: (expiration_date_string, is_auto_selected)
        - expiration_date_string: "YYYY-MM-DD" format or "next_monthly"
        - is_auto_selected: bool indicating if auto-selection needed
    
    Raises:
        ValueError: If date format is invalid
    """
    exp_date = config.get('CALCULATION', 'expiration_date', fallback='next_monthly')
    
    if exp_date.lower() == 'next_monthly':
        return exp_date, True
    else:
        # Validate date format
        validated = validate_date(exp_date)
        if not validated:
            raise ValueError(f"Invalid expiration date format: {exp_date}. Expected YYYY-MM-DD or 'next_monthly'")
        return exp_date, False


def get_data_source_config(config):
    """
    Get data source and related settings from config
    
    Args:
        config: ConfigParser object
    
    Returns:
        dict with keys:
        - source: 'CBOE' or 'YF'
        - expiration_date: string  
        - is_auto_expiration: bool
        - source_specific_config: dict
    
    Raises:
        ValueError: If data source is invalid
    """
    source = config.get('DATA_SOURCE', 'source', fallback='CBOE').upper()
    
    if source not in ['CBOE', 'YF']:
        raise ValueError(f"Invalid data source: {source}. Must be 'CBOE' or 'YF'")
    
    exp_date, is_auto = get_expiration_date_from_config(config)
    
    # Get source-specific config
    if source == 'YF':
        source_config = {
            'cache_downloads': config.getboolean('YAHOO_FINANCE', 'cache_downloads', fallback=True),
            'cache_dir': config.get('YAHOO_FINANCE', 'cache_dir', fallback='data/raw/yf'),
            'cache_expiry_minutes': config.getint('YAHOO_FINANCE', 'cache_expiry_minutes', fallback=60),
            'expiration_selection': config.get('CALCULATION', 'yf_expiration_selection', fallback='nearest'),
            'max_retries': config.getint('YAHOO_FINANCE', 'max_retries', fallback=3),
            'retry_delay_seconds': config.getint('YAHOO_FINANCE', 'retry_delay_seconds', fallback=2),
            'rate_limit_delay': config.getint('YAHOO_FINANCE', 'rate_limit_delay', fallback=1)
        }
    else:  # CBOE
        source_config = {
            'data_dir': config.get('CBOE', 'data_dir', fallback='data/raw/cboe'),
            'base_url': config.get('CBOE', 'base_url', fallback='https://www.cboe.com/delayed_quotes/'),
            'rate_limit_delay': config.getint('CBOE', 'rate_limit_delay', fallback=2),
            'request_timeout': config.getint('CBOE', 'request_timeout', fallback=30)
        }
    
    return {
        'source': source,
        'expiration_date': exp_date,
        'is_auto_expiration': is_auto,
        'source_specific_config': source_config
    }

