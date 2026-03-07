# app/settings.py
import os

class ServerConfig:
    """Server configuration from environment variables"""

    def __init__(self):
        self.llm_api_key = os.getenv("GEMINI_API_KEY")
        self.host = os.getenv("SERVER_HOST", "127.0.0.1")
        self.port = int(os.getenv("SERVER_PORT", "8000"))

        self.title = os.getenv("API_TITLE", "LLM Analysis API")
        self.version = os.getenv("API_VERSION", "0.1.0")
        self.environment = os.getenv("ENVIRONMENT", "development")

        self.debug = self.environment == "development"
        self.allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")

        # 关键配置校验（可选但建议）
        if not self.llm_api_key:
            raise RuntimeError("Missing GEMINI_API_KEY in environment")