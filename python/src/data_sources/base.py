"""
Base adapter class for option data sources

Defines the interface that all data source adapters must implement.
"""

from abc import ABC, abstractmethod
import pandas as pd
import logging


class OptionDataAdapter(ABC):
    """
    Abstract base class for option data adapters
    
    All data source adapters must transform their source-specific data
    into a common format with:
    - ticker: str
    - current_price: float
    - expiration_date: str (YYYY-MM-DD format)
    - option_data: DataFrame with columns [Strike, Call_OI, Put_OI]
    """
    
    def __init__(self, config):
        """
        Initialize adapter with configuration
        
        Args:
            config: dict with source-specific configuration
        """
        self.config = config
        self.logger = logging.getLogger(f'max_pain.{self.__class__.__name__}')
    
    @abstractmethod
    def fetch_option_data(self, ticker, expiration_date):
        """
        Fetch and transform option data into common format
        
        Args:
            ticker: Stock ticker symbol (e.g., "NVDA")
            expiration_date: Expiration date string
                - For auto-selection: "next_monthly"
                - For specific date: "YYYY-MM-DD"
        
        Returns:
            dict with keys:
            - ticker: str
            - current_price: float
            - expiration_date: str (YYYY-MM-DD format, actual expiration used)
            - option_data: DataFrame with columns [Strike, Call_OI, Put_OI]
        
        Raises:
            ValueError: If ticker or expiration_date is invalid
            FileNotFoundError: If data file not found (for file-based sources)
            ConnectionError: If download fails (for API-based sources)
        """
        pass
    
    @abstractmethod
    def get_available_expirations(self, ticker):
        """
        Get list of available expiration dates for a ticker
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            list of str: Expiration dates in YYYY-MM-DD format
        
        Raises:
            ValueError: If ticker is invalid
        """
        pass
    
    def validate_option_data(self, option_data):
        """
        Validate that option data DataFrame has correct format
        
        Args:
            option_data: DataFrame to validate
        
        Returns:
            bool: True if valid
        
        Raises:
            ValueError: If data format is invalid
        """
        required_columns = ['Strike', 'Call_OI', 'Put_OI']
        
        if not isinstance(option_data, pd.DataFrame):
            raise ValueError("option_data must be a pandas DataFrame")
        
        missing_columns = set(required_columns) - set(option_data.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Check for numeric types
        for col in required_columns:
            if not pd.api.types.is_numeric_dtype(option_data[col]):
                raise ValueError(f"Column {col} must be numeric")
        
        # Check for empty data
        if len(option_data) == 0:
            raise ValueError("option_data cannot be empty")
        
        self.logger.debug(f"Validated option data: {len(option_data)} strikes")
        return True
