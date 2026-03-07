from app.llm_models.LLM_communications import LLMCommunications
from app.services.data_processing import DataProcessing

class GeminiAgentCommunication(LLMCommunications):
    """Communication implementation for Gemini Agent"""
    
    def __init__(self, model_name, temperature: float = 0.7, api_key=None):
        super().__init__(model_name=model_name, temperature=temperature)
        # Lazy import so missing optional dependency does not break app startup.
        from google import genai

        self._types = __import__("google.genai.types", fromlist=["GenerateContentConfig"])
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.temperature = temperature
    
    def send_request(self, prompt: str, context: dict = None) -> dict: 
        """Send a request to the Gemini Agent"""
        try:
            response ="reach in send request."
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
                config=self._types.GenerateContentConfig(temperature=self.temperature)
            )
            print(response)
            return response
        except Exception as e:
            print(f"Error sending request to Gemini Agent: {e}")
            return None
