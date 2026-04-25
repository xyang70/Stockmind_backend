# app/config_builder.py
"""
Centralized configuration builders for LLM and database settings.
Removes duplication between server and worker initialization.
"""
import logging
import yaml
from typing import Dict, Any
from app.settings import ServerConfig

logger = logging.getLogger(__name__)


class LLMConfigBuilder:
    """Builds LLM provider configuration from ServerConfig and YAML settings"""
    
    @staticmethod
    def build(config: ServerConfig) -> Dict[str, Any]:
        """
        Build complete LLM model configuration from centralized settings.
        
        Args:
            config: ServerConfig instance with all environment settings
            
        Returns:
            Dictionary with LLM provider configurations
        """
        logger.info("Building LLM model configuration from settings")
        
        with open(config.yaml_config_path, "r") as f:
            llm_model_config = yaml.safe_load(f)

        llm_providers_config = {"open_router": []}
        
        # Load OpenRouter configuration
        open_router_cfg = llm_model_config.get("agents", {})
        open_router_request_url = open_router_cfg.get(
            "request_url",
            "https://openrouter.ai/api/v1"
        )

        for provider_name, models in open_router_cfg.get("providers", {}).items():
            if not isinstance(models, dict):
                logger.warning("Skipping provider '%s' because its models section is not a mapping", provider_name)
                continue
            
            for model_alias, model_cfg in models.items():
                llm_providers_config["open_router"].append({
                    "provider_name": provider_name,
                    "model_alias": model_alias,
                    "model-name": model_cfg["model-name"],
                    "api_key": config.open_router_api_key,
                    "request_url": open_router_request_url,
                })

        # Load Gemini configuration
        llm_providers_config["gemini"] = {
            "provider_name": "gemini",
            "model_name": config.llm_model_name,
            "temperature": 0.7,
            "api_key": config.llm_api_key,
            "request_url": None,
        }

        logger.info("LLM configuration built successfully with %d OpenRouter models", 
                    len(llm_providers_config["open_router"]))
        
        return llm_providers_config
