from abc import ABC,abstractmethod

class BaseDataProvider(ABC):
    @abstractmethod
    def __init__(self, config):
        pass

    @abstractmethod
    def get_data(self):
        pass