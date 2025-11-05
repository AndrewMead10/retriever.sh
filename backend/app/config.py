from pydantic import Field
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
        "http://localhost:8000/auth/google/callback", env="GOOGLE_REDIRECT_URI"
    )
    google_allowed_domains: list[str] = Field(
        default_factory=list, env="GOOGLE_ALLOWED_DOMAINS"
    )

    # RAG / Vector settings
    rag_vector_store_dir: str = Field("data/vector-stores", env="RAG_VECTOR_STORE_DIR")
    rag_model_repo: str = Field("nomic-ai/nomic-embed-text-v1.5-GGUF", env="RAG_MODEL_REPO")
    rag_model_filename: str = Field("nomic-embed-text-v1.5.Q8_0.gguf", env="RAG_MODEL_FILENAME")
    rag_model_dir: str = Field("models", env="RAG_MODEL_DIR")
    rag_embed_dim: int = Field(768, env="RAG_EMBED_DIM")
    rag_hf_token: str = Field("", env="RAG_HF_TOKEN")
    rag_llama_threads: int = Field(4, env="RAG_LLAMA_THREADS")
    rag_llama_batch_size: int = Field(8, env="RAG_LLAMA_BATCH_SIZE")
    rag_llama_context: int = Field(2048, env="RAG_LLAMA_CONTEXT")

    # Polar
    polar_access_token: str = Field("", env="POLAR_ACCESS_TOKEN")
    polar_environment: str = Field("production", env="POLAR_ENVIRONMENT")
    polar_webhook_secret: str = Field("", env="POLAR_WEBHOOK_SECRET")
    polar_product_pro: str = Field("", env="POLAR_PRODUCT_PRO_ID")
    polar_product_topup: str = Field("", env="POLAR_PRODUCT_TOPUP_ID")
    polar_topup_unit_cents: int = Field(0, env="POLAR_TOPUP_UNIT_CENTS")
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

    # Always use .env in project root
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
    )


settings = Settings()
