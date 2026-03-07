# app/main.py
import logging

import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

logger.info("Importing ServerConfig and AnalysisAPIServer")
from app.server import AnalysisAPIServer, ServerConfig

logger.info("Creating ServerConfig")
config = ServerConfig()

logger.info("Creating AnalysisAPIServer")
server = AnalysisAPIServer(config=config)

logger.info("Assigning FastAPI app")
app = server.app

logger.info("main.py import complete")
