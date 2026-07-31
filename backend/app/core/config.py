from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    APP_NAME: str = "DigestAI"
    ENVIRONMENT: str = "development"  # M22: "development" | "production"

    # --- Database (Neon Postgres — required) ---
    DATABASE_URL: str = "postgresql://user:password@localhost/trendmind"

    # --- LLM providers (free tiers) ---
    # Groq: https://console.groq.com/keys 
    GROQ_API_KEY1: Optional[str] = None
    GROQ_API_KEY2: Optional[str] = None
    GROQ_API_KEY3: Optional[str] = None
    GROQ_API_KEY4: Optional[str] = None
    GROQ_API_KEY5: Optional[str] = None

    # Gemini: https://aistudio.google.com/apikey 
    GOOGLE_API_KEY1: Optional[str] = None
    GOOGLE_API_KEY2: Optional[str] = None
    GOOGLE_API_KEY3: Optional[str] = None
    GOOGLE_API_KEY4: Optional[str] = None
    GOOGLE_API_KEY5: Optional[str] = None
    
    # Chroma
    CHROMA_HOST: Optional[str] = None
    CHROMA_API_KEY: Optional[str] = None
    CHROMA_TENANT: Optional[str] = None
    CHROMA_DATABASE: str = "trendmind"
    
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GEMINI_MODEL: str = "gemini-3-flash-preview"

    # --- Parsed key lists (populated in model_post_init) ---
    GROQ_API_KEYS: List[str] = []
    GOOGLE_API_KEYS: List[str] = []
    OPENAI_API_KEY: str = None

    # --- Vector store (local, no API key needed) ---
    CHROMA_PERSIST_DIR: str = "./chroma_data"

    # --- LangSmith (optional, free tier tracing) ---
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "trendmind"
    
    # --- Scheduler ---
    ENABLE_SCHEDULER: bool = False
    PIPELINE_INTERVAL_HOURS: int = 6    
    TRENDS_INTERVAL_HOURS: int = 12       
    GRAPH_INTERVAL_HOURS: int = 12      
    NEWSLETTER_HOUR_UTC: int = 6          
    SCHEDULER_API_KEY: Optional[str] = None

    # --- M22: CORS hardening ---
    ALLOWED_ORIGINS: str = "https://digestai-liard.vercel.app,http://localhost:3000" # Comma-separated list

    RATE_LIMIT_PER_MINUTE: int = 60

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse comma-separated ALLOWED_ORIGINS into a list."""
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"

    def model_post_init(self, __context):
        """Parse GROQ_API_KEY1..5 and GOOGLE_API_KEY1..5 into lists."""
        
        # Parse Groq keys
        groq_keys = []
        for i in range(1, 6):
            key = getattr(self, f"GROQ_API_KEY{i}", None)
            if key:
                groq_keys.append(key)
        self.GROQ_API_KEYS = groq_keys
        
        # Parse Google keys
        google_keys = []
        for i in range(1, 6):
            key = getattr(self, f"GOOGLE_API_KEY{i}", None)
            if key:
                google_keys.append(key)
        self.GOOGLE_API_KEYS = google_keys


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — import and call this, don't instantiate Settings() directly."""
    return Settings()