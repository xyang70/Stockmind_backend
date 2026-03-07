from app.llm_models.LLM_communications import LLMCommunications
from typing import Dict
from app.llm_models.gemini_agent_comm import GeminiAgentCommunication

class LLMModelFactory:

    def __init__(self, config):
        self.config = config
        self._models: Dict[str, LLMCommunications] = {}

    def _normalize_agent(self, agent: str) -> str:
        if agent == "trinity-large-preview-free":
            return "open_router"
        return agent

    def _build_model(self, agent: str) -> LLMCommunications:
        if agent == "gemini":
            gemini_cfg = self.config["gemini"]
            return GeminiAgentCommunication(
                model_name=gemini_cfg["model_name"],
                temperature=gemini_cfg["temperature"],
                api_key=gemini_cfg["api_key"],
            )
        if agent == "open_router":
            # Lazy import so missing optional dependency doesn't break app startup.
            from app.llm_models.open_router_agent_communication import OpenRouterAgentCommunications

            open_router_cfg = self.config["open_router"]
            return OpenRouterAgentCommunications(
                model_name=open_router_cfg["model_name"],
                temperature=open_router_cfg["temperature"],
                api_key=open_router_cfg["api_key"],
                request_url=open_router_cfg["request_url"],
            )
        raise ValueError(f"Unsupported LLM model: {agent}")

    def get_llm_model(self, agent: str) -> LLMCommunications:
        """Factory method to create/cached LLM model instances based on configuration."""
        normalized_agent = self._normalize_agent(agent)
        if normalized_agent not in self._models:
            self._models[normalized_agent] = self._build_model(normalized_agent)
        return self._models[normalized_agent]
