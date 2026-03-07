
from app.data_providers.data_provider import BaseDataProvider
from app.data_providers.yfinance_data_provider import YFinanceDataProvider
from typing import Dict

class DataProviderFactory:
    """Factory for creating data provider instances based on configuration"""
    def __init__(self):
            self.config = {"ticker":"NVDA"}
            self._providers: Dict[str, BaseDataProvider] = {
            "yfinance": YFinanceDataProvider(self.config),
        }
 
    def create_data_provider(self,provider_type: str) -> BaseDataProvider:
        """Create a data provider instance based on the specified type"""
        if provider_type in self._providers:
            return self._providers[provider_type]
        else:
            raise ValueError(f"Unsupported data provider type: {provider_type}")