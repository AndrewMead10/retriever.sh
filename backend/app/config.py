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
    r2_images_bucket: str = Field("", env="R2_IMAGES_BUCKET")
    r2_images_public_base_url: str = Field("", env="R2_IMAGES_PUBLIC_BASE_URL")
    r2_images_presign_ttl_seconds: int = Field(3600, env="R2_IMAGES_PRESIGN_TTL_SECONDS")
    
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

    # RAG / Vector settings
    rag_model_repo: str = Field("nomic-ai/nomic-embed-text-v1.5-GGUF", env="RAG_MODEL_REPO")
    rag_model_filename: str = Field("nomic-embed-text-v1.5.Q8_0.gguf", env="RAG_MODEL_FILENAME")
    rag_model_dir: str = Field("models", env="RAG_MODEL_DIR")
    rag_embed_dim: int = Field(256, env="RAG_EMBED_DIM")
    rag_hf_token: str = Field("", env="RAG_HF_TOKEN")
    rag_llama_threads: int = Field(4, env="RAG_LLAMA_THREADS")
    rag_llama_batch_size: int = Field(8, env="RAG_LLAMA_BATCH_SIZE")
    rag_llama_context: int = Field(2048, env="RAG_LLAMA_CONTEXT")
    rag_image_model_id: str = Field("google/siglip2-base-patch16-naflex", env="RAG_IMAGE_MODEL_ID")
    rag_image_model_dir: str = Field("models/siglip2", env="RAG_IMAGE_MODEL_DIR")
    rag_image_embed_dim: int = Field(768, env="RAG_IMAGE_EMBED_DIM")
    rag_image_device: str = Field("cpu", env="RAG_IMAGE_DEVICE")
    rag_image_dtype: str = Field("float32", env="RAG_IMAGE_DTYPE")
    rag_image_max_bytes: int = Field(10 * 1024 * 1024, env="RAG_IMAGE_MAX_BYTES")
    rag_image_allowed_mime_types: list[str] = Field(
        default_factory=lambda: ["image/jpeg", "image/png", "image/webp", "image/gif"],
        env="RAG_IMAGE_ALLOWED_MIME_TYPES",
    )

    # Vespa
    vespa_endpoint: str = Field("http://localhost:8080", env="VESPA_ENDPOINT")
    vespa_namespace: str = Field("rag", env="VESPA_NAMESPACE")
    vespa_document_type: str = Field("rag_document", env="VESPA_DOCUMENT_TYPE")
    vespa_rank_profile: str = Field("rag-hybrid", env="VESPA_RANK_PROFILE")
    vespa_timeout_seconds: float = Field(10.0, env="VESPA_TIMEOUT_SECONDS")
    vespa_embedding_dim: int = Field(256, env="VESPA_EMBED_DIM")
    vespa_image_document_type: str = Field("rag_image", env="VESPA_IMAGE_DOCUMENT_TYPE")
    vespa_image_rank_profile: str = Field("rag-image", env="VESPA_IMAGE_RANK_PROFILE")
    vespa_image_embedding_dim: int = Field(768, env="VESPA_IMAGE_EMBED_DIM")

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
