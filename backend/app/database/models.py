from uuid6 import uuid7
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class AuditMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class User(Base, AuditMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    email_verification_token = Column(String, unique=True, nullable=True, index=True)
    email_verification_token_expires_at = Column(DateTime, nullable=True)
    name = Column(String, nullable=True)

    roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    subscription = relationship("UserSubscription", back_populates="user", uselist=False)
    usage = relationship("UserUsage", back_populates="user", uselist=False)


class Role(Base, AuditMixin):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    parent_role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)

    parent = relationship("Role", remote_side=[id])


class UserRole(Base):
    __tablename__ = "user_roles"
    
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    user = relationship("User", back_populates="roles")
    role = relationship("Role")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    token = Column(String, unique=True)
    expires_at = Column(DateTime, index=True)
    used = Column(Boolean, default=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)




class Plan(Base, AuditMixin):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True)
    slug = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    price_cents = Column(Integer, nullable=False, default=0)
    polar_product_id = Column(String, nullable=True)
    query_qps_limit = Column(Integer, nullable=False)
    ingest_qps_limit = Column(Integer, nullable=False)
    project_limit = Column(Integer, nullable=False)
    vector_limit = Column(Integer, nullable=False)

    subscriptions = relationship("UserSubscription", back_populates="plan")


class UserSubscription(Base, AuditMixin):
    __tablename__ = "user_subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    status = Column(String, nullable=False, default="active")
    polar_customer_id = Column(String, nullable=True)
    polar_subscription_id = Column(String, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, nullable=False, default=False)

    user = relationship("User", back_populates="subscription")
    plan = relationship("Plan", back_populates="subscriptions")


class UserUsage(Base, AuditMixin):
    __tablename__ = "user_usage"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    total_queries = Column(Integer, nullable=False, default=0)
    total_ingest_requests = Column(Integer, nullable=False, default=0)
    total_vectors = Column(Integer, nullable=False, default=0)
    last_reset = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="usage")


class RateLimitBucket(Base):
    __tablename__ = "rate_limit_buckets"
    __table_args__ = (UniqueConstraint("user_id", "limit_type", name="uq_rate_limit_user_type"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    limit_type = Column(String, nullable=False)  # e.g. "query", "ingest"
    tokens = Column(Float, nullable=False)
    last_refill = Column(DateTime, nullable=False, default=datetime.utcnow)
    max_tokens = Column(Integer, nullable=False)

    user = relationship("User", backref="rate_limit_buckets")


class Project(Base, AuditMixin):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid7()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    slug = Column(String, nullable=True)
    embedding_provider = Column(String, nullable=False)
    embedding_model = Column(String, nullable=False)
    embedding_model_repo = Column(String, nullable=True)
    embedding_model_file = Column(String, nullable=True)
    embedding_dim = Column(Integer, nullable=False)
    hybrid_weight_vector = Column(Float, nullable=False, default=0.5)
    hybrid_weight_text = Column(Float, nullable=False, default=0.5)
    top_k_default = Column(Integer, nullable=False, default=10)
    vector_search_k = Column(Integer, nullable=False, default=50)
    vector_store_path = Column(String, nullable=False)
    vector_count = Column(Integer, nullable=False, default=0)
    ingest_api_key_hash = Column(String, nullable=False)
    last_ingest_at = Column(DateTime, nullable=True)
    active = Column(Boolean, nullable=False, default=True)

    user = relationship("User", back_populates="projects")
    api_keys = relationship("ProjectApiKey", back_populates="project", cascade="all, delete-orphan")
    documents = relationship("ProjectDocument", back_populates="project", cascade="all, delete-orphan")
    images = relationship("ProjectImage", back_populates="project", cascade="all, delete-orphan")


class ProjectApiKey(Base, AuditMixin):
    __tablename__ = "project_api_keys"

    id = Column(Integer, primary_key=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    name = Column(String, nullable=False)
    prefix = Column(String, nullable=False)
    hashed_key = Column(String, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    revoked = Column(Boolean, nullable=False, default=False)

    project = relationship("Project", back_populates="api_keys")


class ProjectDocument(Base, AuditMixin):
    __tablename__ = "project_documents"

    id = Column(Integer, primary_key=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    vespa_document_id = Column(String, nullable=False, unique=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict)
    active = Column(Boolean, nullable=False, default=True)

    project = relationship("Project", back_populates="documents")


class ProjectImage(Base, AuditMixin):
    __tablename__ = "project_images"

    id = Column(Integer, primary_key=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    vespa_document_id = Column(String, nullable=False, unique=True)
    storage_key = Column(String, nullable=False, unique=True)
    content_type = Column(String, nullable=False)
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict)
    active = Column(Boolean, nullable=False, default=True)

    project = relationship("Project", back_populates="images")
