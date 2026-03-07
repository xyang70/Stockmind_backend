


from pydantic import BaseModel

class LLMAgentRequest(BaseModel):
    agent_name: str
    model: str

class AnalysisRequest(BaseModel):
    symbol: str
    llm_agent_request: LLMAgentRequest


