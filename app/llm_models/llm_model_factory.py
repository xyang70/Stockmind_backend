from app.llm_models.LLM_communications import LLMCommunications
from typing import Dict
from app.llm_models.gemini_agent_comm import GeminiAgentCommunication

class LLMModelFactory:

    def __init__(self, config):
        self.config = config
        self._models: Dict[str, LLMCommunications] = {}

    def _normalize_agent(self, agent: str, model: str) -> str:
        return f"{agent}_{model}".lower()

    def _normalize_lookup_value(self, value) -> str:
        if value is None:
            return ""
        return str(value).strip().lower()

    def _build_model(self, agent: str, model_name: str) -> LLMCommunications:
        normalized_agent = self._normalize_agent(agent, model_name)
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

            # config['open_router'] is expected to be a list of provider model dicts
            open_router_list = self.config.get("open_router", [])
            requested_model = self._normalize_lookup_value(model_name)

            def _model_matches(model_cfg: dict) -> bool:
                if not isinstance(model_cfg, dict):
                    return False

                candidates = (
                    model_cfg.get("model_alias"),
                    model_cfg.get("model-name"),
                    model_cfg.get("model_name"),
                )
                return requested_model in {
                    self._normalize_lookup_value(candidate) for candidate in candidates
                }

            # Match by possible keys produced by server: 'model-name' or 'model_name' or 'model_alias'
            match = next(
                (
                    m
                    for m in open_router_list
                    if _model_matches(m)
                ),
                None,
            )

            if not match:
                available_models = sorted(
                    {
                        str(candidate).strip()
                        for entry in open_router_list
                        if isinstance(entry, dict)
                        for candidate in (
                            entry.get("model_alias"),
                            entry.get("model-name"),
                            entry.get("model_name"),
                        )
                        if candidate
                    }
                )
                raise ValueError(
                    f"Model {model_name} not found in OpenRouter configuration. "
                    f"Available models: {', '.join(available_models)}"
                )

            # Construct communicator using the matched provider entry
            selected_model_name = match.get("model-name") or match.get("model_name") or match.get("model_alias")
            temp = match.get("temperature", 0.7)
            api_key = match.get("api_key")
            request_url = match.get("request_url")

            return OpenRouterAgentCommunications(
                model_name=selected_model_name,
                temperature=temp,
                api_key=api_key,
                request_url=request_url,
            )
        raise ValueError(f"Unsupported LLM model: {agent}")

    def get_llm_model(self, agent: str, model_name: str) -> LLMCommunications:
        """Factory method to create/cached LLM model instances based on configuration."""
        normalized_agent = self._normalize_agent(agent, model_name)
        print(f"Requesting LLM model with agent: {agent}, model_name: {model_name}. Normalized key: {normalized_agent}")
        if normalized_agent not in self._models:
            self._models[normalized_agent] = self._build_model(agent=agent,model_name=model_name)
        
        return self._models[normalized_agent]
