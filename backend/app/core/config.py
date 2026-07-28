from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    APP_NAME: str = "TrendMind"
    ENVIRONMENT: str = "development"

    # --- Database (Neon Postgres — required) ---
    # Get this from your Neon project dashboard:
    # https://console.neon.tech -> Project -> Connection Details
    # Format: postgresql://user:password@ep-xxxx.region.aws.neon.tech/dbname?sslmode=require
    DATABASE_URL: str = "postgresql://user:password@localhost/trendmind"

    # --- LLM providers (free tiers) ---
    # Groq: https://console.groq.com/keys 
    GROQ_API_KEY: str | None = None

    # Gemini: https://aistudio.google.com/apikey 
    GEMINI_API_KEY: str | None = None

    # --- Vector store (local, no API key needed) ---
    CHROMA_PERSIST_DIR: str = "./chroma_data"

    # --- LangSmith (optional, free tier tracing) ---
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str | None = None
    LANGCHAIN_PROJECT: str = "trendmind"
    ENABLE_SCHEDULER: bool = False
 
    PIPELINE_INTERVAL_HOURS: int = 6    
    TRENDS_INTERVAL_HOURS: int = 12       
    GRAPH_INTERVAL_HOURS: int = 12      
    NEWSLETTER_HOUR_UTC: int = 6          
 
    SCHEDULER_API_KEY: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — import and call this, don't instantiate Settings() directly."""
    return Settings()
