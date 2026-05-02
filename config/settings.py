import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")




class DatabaseConfig:
    HOST = os.getenv("DB_HOST", "localhost")
    PORT = int(os.getenv("DB_PORT", 5432))
    NAME = os.getenv("DB_NAME", "university_obs")
    USER = os.getenv("DB_USER", "postgres")
    PASSWORD = os.getenv("DB_PASSWORD", "yourpassword")
    URL = os.getenv(
        "DATABASE_URL",
        f"postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{NAME}"
    )

    POOL_SIZE = 10
    MAX_OVERFLOW = 20
    POOL_TIMEOUT = 30


class FlaskConfig:
    ENV = os.getenv("FLASK_ENV", "development")
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
    HOST = os.getenv("API_HOST", "0.0.0.0")
    PORT = int(os.getenv("API_PORT", 5000))
    DEBUG = ENV == "development"


class AgentConfig:
    SCRAPE_INTERVAL = int(os.getenv("AGENT_SCRAPE_INTERVAL", 3600))
    MAX_RESEARCHERS = int(os.getenv("AGENT_MAX_RESEARCHERS", 500))
    CLUSTERING_N_CLUSTERS = int(os.getenv("CLUSTERING_N_CLUSTERS", 8))
    COLLAB_TOP_N = int(os.getenv("COLLAB_TOP_N", 5))
    SCRAPE_DELAY_SECONDS = 2


class LogConfig:
    LEVEL = os.getenv("LOG_LEVEL", "INFO")
    FILE = os.getenv("LOG_FILE", "logs/observatory.log")
    ROTATION = "10 MB"
    RETENTION = "1 month"


class Settings:
    db = DatabaseConfig()
    flask = FlaskConfig()
    agents = AgentConfig()
    log = LogConfig()


settings = Settings()