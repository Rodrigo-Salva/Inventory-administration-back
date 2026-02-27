from typing import List
from pydantic_settings import BaseSettings
from pydantic import field_validator
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # Application
    app_name: str = "Inventory SaaS"
    app_version: str = "1.0.0"
    environment: str = "development"  # development, staging, production
    debug: bool = True
    api_v1_str: str = "/api/v1"
    
    # Database
    database_url: str
    db_pool_size: int = 5
    db_max_overflow: int = 10
    
    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    cors_origins: List[str] | str = ["*"]
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            import json
            try:
                # Intentar parsear como JSON (para formato ["http..."])
                return json.loads(v)
            except json.JSONDecodeError:
                # Fallback a separado por comas
                return [origin.strip() for origin in v.split(",")]
        return v
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 300  # 5 minutos
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 60
    
    # Logging
    log_level: str = "INFO"
    
    # Pagination
    default_page_size: int = 10
    max_page_size: int = 500
    
    # Stock Alerts
    low_stock_threshold_percentage: float = 0.2  # 20% del stock mínimo
    
    # File Upload (para futuras features)
    max_upload_size_mb: int = 5
    allowed_image_extensions: List[str] | str = ["jpg", "jpeg", "png", "webp"]

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignorar campos extra del .env


settings = Settings()