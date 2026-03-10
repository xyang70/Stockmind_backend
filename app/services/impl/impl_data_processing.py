from app.services.data_processing import DataProcessing
from app.signals.trend import ema_trend_signal
from app.indicators.calculate_ema import calculate_ema
import pandas as pd
from app.experimentals.pandas_ta_test import MarketAnalyzer
class DataProcessingImpl(DataProcessing):
    def __init__(self):
        super().__init__()
        self.market_analyzer = MarketAnalyzer()  # Initialize the MarketAnalyzer instance if needed

    def process_data(self, symbol: str, data: pd.DataFrame) -> dict:
        # Implement your data processing logic here
        # For example, you can perform data cleaning, feature engineering, etc.
        # df = pd.DataFrame(data)
        # data_output = ema_trend_signal(calculate_ema(df), fast_period=5, slow_period=20, as_of=df.index[-1].isoformat())
        # return data_output
        return self.market_analyzer.analyze_technical_indicators(symbol,data)  # Example of using the MarketAnalyzer for analysis
        
    

