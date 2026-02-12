from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    
    # Tell Pydantic to read .env file if it exists
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # arXiv settings
    arxiv_max_results: int = 30
    arxiv_delay_seconds: float = 3.0
    arxiv_hours_back: int = 24
    
    # Database
    database_url: str = "postgresql://localhost:5432/arxiv_digest"


# Global instance - import this anywhere you need config
settings = Settings()
