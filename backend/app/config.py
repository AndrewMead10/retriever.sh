from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    # JWT Configuration
    jwt_secret: str = Field(..., env="JWT_SECRET")
    access_token_ttl_minutes: int = Field(15, env="ACCESS_TOKEN_TTL_MINUTES")
    refresh_token_ttl_days: int = Field(30, env="REFRESH_TOKEN_TTL_DAYS")
    
    # Database
    database_url: str = Field(
        "postgresql+psycopg://postgres:postgres@localhost:5432/rag",
        env="DATABASE_URL",
    )

    # CORS
    cors_origins: list[str] = Field(["*"], env="CORS_ORIGINS")
    cors_allow_credentials: bool = Field(True, env="CORS_ALLOW_CREDENTIALS")
    
    # Feature Flags
    enable_user_registration: bool = Field(True, env="ENABLE_USER_REGISTRATION")
    enable_password_reset: bool = Field(True, env="ENABLE_PASSWORD_RESET")
    enable_admin_panel: bool = Field(True, env="ENABLE_ADMIN_PANEL")
    enable_backups: bool = Field(True, env="ENABLE_BACKUPS")
    
    # R2 Backup (optional)
    enable_r2_backup: bool = Field(False, env="ENABLE_R2_BACKUP")
    r2_account_id: str = Field("", env="R2_ACCOUNT_ID")
    r2_access_key_id: str = Field("", env="R2_ACCESS_KEY_ID")
    r2_secret_access_key: str = Field("", env="R2_SECRET_ACCESS_KEY")
    r2_bucket: str = Field("", env="R2_BUCKET")
    
    # Email (SES)
    ses_from_email: str = Field("", env="SES_FROM_EMAIL")
    aws_access_key_id: str = Field("", env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field("", env="AWS_SECRET_ACCESS_KEY")
    aws_default_region: str = Field("us-east-1", env="AWS_DEFAULT_REGION")
    frontend_url: str = Field("http://localhost:3000", env="FRONTEND_URL")

    # Cookies
    cookie_secure: bool = Field(False, env="COOKIE_SECURE")
    
    # Google OAuth
    google_client_id: str = Field("", env="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field("", env="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(
        "http://localhost:5656/api/auth/google/callback", env="GOOGLE_REDIRECT_URI"
    )
    google_allowed_domains: list[str] = Field(
        default_factory=list, env="GOOGLE_ALLOWED_DOMAINS"
    )

    # RAG / Embedding settings
    rag_embedding_base_url: str = Field(
        "https://embedding-server.amqm.dev",
        env="RAG_EMBEDDING_BASE_URL",
    )
    rag_embedding_api_key: str = Field(
        "",
        env="RAG_EMBEDDING_API_KEY",
    )
    rag_embedding_model: str = Field(
        "jinaai/jina-embeddings-v5-text-small-retrieval-mlx",
        env="RAG_EMBEDDING_MODEL",
    )
    rag_embed_dim: int = Field(512, env="RAG_EMBED_DIM")
    rag_embedding_timeout_seconds: float = Field(30.0, env="RAG_EMBEDDING_TIMEOUT_SECONDS")

    # Vespa
    vespa_endpoint: str = Field("http://localhost:8080", env="VESPA_ENDPOINT")
    vespa_namespace: str = Field("rag", env="VESPA_NAMESPACE")
    vespa_document_type: str = Field("rag_document", env="VESPA_DOCUMENT_TYPE")
    vespa_rank_profile: str = Field("rag-hybrid", env="VESPA_RANK_PROFILE")
    vespa_timeout_seconds: float = Field(10.0, env="VESPA_TIMEOUT_SECONDS")
    vespa_embedding_dim: int = Field(512, env="VESPA_EMBED_DIM")

    # Polar
    polar_access_token: str = Field("", env="POLAR_ACCESS_TOKEN")
    polar_environment: str = Field("production", env="POLAR_ENVIRONMENT")
    polar_webhook_secret: str = Field("", env="POLAR_WEBHOOK_SECRET")
    polar_product_tinkering: str = Field(
        "",
        validation_alias=AliasChoices(
            "POLAR_PRODUCT_TINKERING_ID",
            "POLAR_PRODUCT_TINKERING",
        ),
    )
    polar_product_building: str = Field(
        "",
        validation_alias=AliasChoices("POLAR_PRODUCT_BUILDING_ID", "POLAR_PRODUCT_BUILDING"),
    )
    polar_product_scale: str = Field(
        "",
        validation_alias=AliasChoices(
            "POLAR_PRODUCT_SCALE_ID",
            "POLAR_PRODUCT_SCALE",
            "POLAR_PRODUCT_ENTERPRISE_ID",
            "POLAR_PRODUCT_ENTERPRISE",
        ),
    )
    polar_success_url: str = Field("http://localhost:3000/billing/success", env="POLAR_SUCCESS_URL")
    polar_cancel_url: str = Field("http://localhost:3000/billing", env="POLAR_CANCEL_URL")
    polar_organization_slug: str = Field("", env="POLAR_ORGANIZATION_SLUG")
    polar_portal_return_url: str = Field("http://localhost:3000/billing", env="POLAR_PORTAL_RETURN_URL")

    # LogFire Configuration
    logfire_enabled: bool = Field(False, env="LOGFIRE_ENABLED")
    logfire_token: str = Field("", env="LOGFIRE_TOKEN")
    logfire_environment: str = Field("development", env="LOGFIRE_ENVIRONMENT")
    logfire_service_name: str = Field("rag-app", env="LOGFIRE_SERVICE_NAME")
    logfire_ignore_no_config: bool = Field(True, env="LOGFIRE_IGNORE_NO_CONFIG")

    # Try .env in project root for local development, but don't fail if not found (Docker uses env injection)
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        env_file_ignore_missing=True,
    )


settings = Settings()
