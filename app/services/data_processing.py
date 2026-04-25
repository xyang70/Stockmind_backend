from abc import ABC, abstractmethod


class DataProcessing(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def process_data(self, data) -> dict:
        pass
    