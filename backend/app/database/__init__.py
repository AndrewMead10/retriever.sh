from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from .models import Base
from ..config import settings
from ..logging_config import instrument_sqlalchemy

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
)

# Instrument SQLAlchemy with LogFire
instrument_sqlalchemy(engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@event.listens_for(engine, "connect")
def _setup_extensions(dbapi_conn, connection_record):
    with dbapi_conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    register_vector(dbapi_conn)

@contextmanager
def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
