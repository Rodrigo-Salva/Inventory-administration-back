from decimal import Decimal
from typing import Dict, List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
        env_ignore_empty=True,  # una variable vacía (p. ej. desde Docker) equivale a "no definida"
    )
    # Application
    app_name: str = "Inventory SaaS"
    app_version: str = "1.0.0"
    environment: str = "development"  # development, staging, production
    debug: bool = False
    api_v1_str: str = "/api/v1"
    
    # Database
    database_url: str
    db_pool_size: int = 5
    db_max_overflow: int = 10
    sql_echo: bool = False
    
    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    cors_origins: List[str] | str = []

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value):
        """Acepta los valores heredados de entorno sin habilitar debug por error."""
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "production", "prod", "false", "0", "no"}:
                return False
            if normalized in {"development", "dev", "true", "1", "yes"}:
                return True
        return value
    
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
    
    # Límite de intentos de login/registro por IP (protege contra fuerza bruta)
    auth_rate_limit: str = "5/minute"

    # Logging
    log_level: str = "INFO"

    # Correo (alertas de stock). Sin SMTP_USER/SMTP_PASSWORD no se envían correos.
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None
    
    # Stock Alerts
    low_stock_threshold_percentage: float = 0.2  # 20% del stock mínimo
    
    # File Upload (para futuras features)
    max_upload_size_mb: int = 5
    allowed_image_extensions: List[str] | str = ["jpg", "jpeg", "png", "webp"]
    
    # AI (Gemini)
    google_api_key: Optional[str] = None
    
    # Observability
    sentry_dsn: Optional[str] = None
    prometheus_enabled: bool = True

    # Docs / API explorer (se deshabilita en producción)
    enable_docs: bool = True

    # Mercado Pago
    mp_access_token: Optional[str] = None
    mp_public_key: Optional[str] = None
    mp_webhook_secret: Optional[str] = None  # secreto de firma de webhooks (panel de MP)
    # Planes de suscripción {"premium": 49.90}. El precio lo define el servidor, no el cliente.
    subscription_plans: Dict[str, Decimal] = {}
    subscription_currency: str = "PEN"

    # Datos de ejemplo (python -m app.infrastructure.seeds.seed_data)
    seed_admin_email: str = "admin@demo.com"
    seed_admin_password: Optional[str] = None  # si falta, se genera una aleatoria y se muestra una vez

    @model_validator(mode="after")
    def validate_production_security(self):
        """En producción exige secretos fuertes y CORS explícito."""
        if self.environment.lower() == "production":
            if len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY debe tener al menos 32 caracteres en producción")
            if "*" in (self.cors_origins or []):
                raise ValueError("CORS_ORIGINS no puede ser '*' en producción")
        return self


settings = Settings()
