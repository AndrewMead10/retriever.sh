import logfire
from sqlalchemy import create_engine
from .config import settings


def setup_logfire():
    """Configure LogFire with automatic instrumentation"""
    if not settings.logfire_enabled:
        return

    # Configure LogFire
    logfire.configure(
        service_name=settings.logfire_service_name,
        service_version="1.0.0",
        token=settings.logfire_token if settings.logfire_token else None,
        # Only send to external service in production if token is provided
        send_to_logfire=bool(settings.logfire_token) and settings.logfire_environment == "production",
    )

    # # Log initialization
    # logfire.info("LogFire initialized", {
    #     "environment": settings.logfire_environment,
    #     "service_name": settings.logfire_service_name,
    #     "send_to_logfire": bool(settings.logfire_token)
    # })
    #

def instrument_sqlalchemy(engine):
    """Instrument SQLAlchemy engine with LogFire"""
    if not settings.logfire_enabled:
        return engine

    logfire.instrument_sqlalchemy(engine=engine)
    logfire.info("SQLAlchemy instrumented with LogFire")
    return engine
