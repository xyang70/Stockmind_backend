from app.services.data_processing import DataProcessing
from app.signals.trend import ema_trend_signal
from app.indicators.calculate_ema import calculate_ema
import pandas as pd
from app.experimentals.pandas_ta_test import MarketAnalyzer
class DataProcessingImpl(DataProcessing):
    def __init__(self):
        super().__init__()
        self.market_analyzer = MarketAnalyzer()  

    def process_data(self, symbol: str, data: pd.DataFrame) -> dict:

        return self.market_analyzer.analyze_technical_indicators(symbol,data)  
        
    

