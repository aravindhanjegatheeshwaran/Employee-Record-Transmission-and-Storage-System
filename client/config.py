# client/config.py
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import logging
from enum import Enum
import json
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('client.log')
    ]
)
logger = logging.getLogger(__name__)


class CommunicationMode(str, Enum):
    """Enum for communication mode"""
    HTTP = "http"
    WEBSOCKET = "websocket"
    KAFKA = "kafka"


class ClientSettings(BaseSettings):
    """Client settings"""
    # Server connection
    SERVER_URL: str = os.getenv("SERVER_URL", "http://localhost:8000")
    API_TOKEN: Optional[str] = os.getenv("API_TOKEN", None)
    COMM_MODE: CommunicationMode = CommunicationMode(os.getenv("COMM_MODE", "http"))
    
    # CSV file settings
    CSV_FILE_PATH: str = os.getenv("CSV_FILE_PATH", "employee_data.csv")
    CSV_DELIMITER: str = os.getenv("CSV_DELIMITER", ",")
    CSV_ENCODING: str = os.getenv("CSV_ENCODING", "utf-8")
    
    # Processing settings
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "50"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY: float = float(os.getenv("RETRY_DELAY", "1.0"))
    TIMEOUT: float = float(os.getenv("TIMEOUT", "10.0"))
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "10"))
    
    # Kafka settings (used only if COMM_MODE is "kafka")
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_TOPIC: str = os.getenv("KAFKA_TOPIC", "employee-records")
    
    # WebSocket settings (used only if COMM_MODE is "websocket")
    WS_URL: str = os.getenv("WS_URL", "ws://localhost:8000/ws")
    
    # Authentication settings
    AUTH_USERNAME: str = os.getenv("AUTH_USERNAME", "admin")
    AUTH_PASSWORD: str = os.getenv("AUTH_PASSWORD", "adminpassword")
    
    class Config:
        """Pydantic config"""
        env_file = ".env"


# Create instance of settings
settings = ClientSettings()

# Print configuration (excluding sensitive information)
config_dict = settings.dict()
config_dict.pop("API_TOKEN", None)
config_dict.pop("AUTH_PASSWORD", None)

logger.info(f"Client configuration loaded: {json.dumps(config_dict, indent=2, default=str)}")
