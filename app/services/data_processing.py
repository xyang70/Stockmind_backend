from abc import ABC, abstractmethod


class DataProcessing(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def process_data(self, data) -> dict:
        # Implement your data processing logic here
        # For example, you can perform data cleaning, feature engineering, etc.
        # df = pd.DataFrame(data)
        # data_output = ema_trend_signal(calculate_ema(df), fast_period=5, slow_period=20, as_of=df.index[-1].isoformat())
        # return data_output
        pass
    