"""
Data source factory

Creates appropriate adapter based on configuration.
"""

from .base import OptionDataAdapter
from .cboe_adapter import CBOEAdapter
from .yf_adapter import YahooFinanceAdapter


class DataSourceFactory:
    """
    Factory to create appropriate data adapter based on config
    
    Ensures only one data source is used per execution.
    """
    
    @staticmethod
    def create_adapter(source, config):
        """
        Create data adapter based on source type
        
        Args:
            source: 'CBOE' or 'YF'
            config: dict with source-specific configuration
        
        Returns:
            OptionDataAdapter instance (CBOEAdapter or YahooFinanceAdapter)
        
        Raises:
            ValueError: If source is unknown
        """
        if source == 'CBOE':
            return CBOEAdapter(config)
        elif source == 'YF':
            return YahooFinanceAdapter(config)
        else:
            raise ValueError(f"Unknown data source: {source}. Must be 'CBOE' or 'YF'")
