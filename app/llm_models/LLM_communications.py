from abc import ABC, abstractmethod

class LLMCommunications(ABC):

    def __init__(self, model_name: str, temperature: float = 0.7):
        pass

    @abstractmethod
    def send_request(self, prompt):
        pass

    # @abstractmethod
    # def receive_response(self):
    #     pass