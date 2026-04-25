from abc import ABC,abstractmethod


class AnalysisService(ABC):
    def __init__(self, data_processor=None,llm_agent=None,data_provider=None):
        pass

    @abstractmethod
    def analyze_data(self, data):
        # Implement your analysis logic here
        pass
    # @abstractmethod
    # def save_results(self, results):
    #     pass

    @abstractmethod
    def get_results(self, query):
        pass
