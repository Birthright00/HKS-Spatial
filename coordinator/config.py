"""
Shared configuration for all services.
Loads environment variables from the root .env file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from repository root
ROOT_DIR = Path(__file__).parent.parent
ENV_PATH = ROOT_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    print(f"Warning: .env file not found at {ENV_PATH}")

# Service configuration
class ServiceConfig:
    """Configuration for microservices"""

    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    # ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    NANOBANANA_API_KEY = os.getenv("NANOBANANA_API_KEY", "")
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

    # Service ports
    RAG_SERVICE_PORT = int(os.getenv("RAG_SERVICE_PORT", "8001"))
    IMAGE_GEN_SERVICE_PORT = int(os.getenv("IMAGE_GEN_SERVICE_PORT", "8002"))
    COORDINATOR_PORT = int(os.getenv("COORDINATOR_PORT", "8000"))

    # Service hosts
    RAG_SERVICE_HOST = os.getenv("RAG_SERVICE_HOST", "127.0.0.1")
    IMAGE_GEN_SERVICE_HOST = os.getenv("IMAGE_GEN_SERVICE_HOST", "127.0.0.1")
    COORDINATOR_HOST = os.getenv("COORDINATOR_HOST", "0.0.0.0")

    # Paths
    RAG_LANGCHAIN_PATH = ROOT_DIR / "RAG-Langchain"
    IMAGE_GEN_PATH = ROOT_DIR / "picture-generation-verbose-api-module"

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []

        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY not set")
        if not cls.NANOBANANA_API_KEY:
            errors.append("NANOBANANA_API_KEY not set")

        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")

        return True

    @classmethod
    def get_service_urls(cls):
        """Get all service URLs"""
        return {
            "rag": f"http://{cls.RAG_SERVICE_HOST}:{cls.RAG_SERVICE_PORT}",
            "image_gen": f"http://{cls.IMAGE_GEN_SERVICE_HOST}:{cls.IMAGE_GEN_SERVICE_PORT}",
        }
