
from app.llm_models.LLM_communications import LLMCommunications
from openai import OpenAI

class OpenRouterAgentCommunications(LLMCommunications):
    """Communication implementation for OpenRouter Agent"""
    
    def __init__(self, model_name, temperature: float = 0.7, api_key=None, request_url: str = None):
        super().__init__(model_name=model_name, temperature=temperature)
        # Additional initialization for OpenRouter Agent if needed
        self.model_name = model_name
        self.temperature = temperature
        self.request_url = request_url
        self.client = OpenAI(base_url=request_url,api_key=api_key)  # Initialize OpenAI client with API key

    def send_request(self, prompt: str, context: dict = None) -> dict: 
        """Send a request to the OpenRouter Agent"""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                extra_body={"temperature": self.temperature,
                            "reasoning":{"enabled": True}}
            )
            print(response)
            return response
        except Exception as e:
            print(f"Error sending request to OpenRouter Agent: {e}")
            return None